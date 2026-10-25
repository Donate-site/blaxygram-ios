@interface MTBlaxyWebSocket: NSObject<MTTcpConnectionInterface, NSURLSessionWebSocketDelegate> {
    __weak id<MTTcpConnectionInterfaceDelegate> _delegate;
    dispatch_queue_t _queue;
    NSURLSession *_session;
    NSURLSessionWebSocketTask *_task;
    NSMutableData *_incoming;
    NSMutableArray<NSDictionary *> *_reads;
    NSMutableArray<NSData *> *_writes;
    NSUInteger _queuedBytes;
    bool _sending;
    bool _closed;
    bool _opened;
    bool _draining;
}
- (instancetype)initWithDelegate:(id<MTTcpConnectionInterfaceDelegate>)delegate queue:(dispatch_queue_t)queue;
@end

@implementation MTBlaxyWebSocket
- (instancetype)initWithDelegate:(id<MTTcpConnectionInterfaceDelegate>)delegate queue:(dispatch_queue_t)queue {
    self = [super init];
    if (self) {
        _delegate = delegate;
        _queue = queue;
        _incoming = [[NSMutableData alloc] init];
        _reads = [[NSMutableArray alloc] init];
        _writes = [[NSMutableArray alloc] init];
    }
    return self;
}
- (void)setGetLogPrefix:(NSString *(^)())getLogPrefix {}
- (void)setUsageCalculationInfo:(MTNetworkUsageCalculationInfo *)usageCalculationInfo {}
- (bool)connectToHost:(NSString *)host onPort:(uint16_t)port viaInterface:(NSString *)interface withTimeout:(NSTimeInterval)timeout error:(NSError **)error {
    if (_session || _closed) return false;
    NSURLSessionConfiguration *configuration = [NSURLSessionConfiguration ephemeralSessionConfiguration];
    configuration.timeoutIntervalForRequest = timeout;
    configuration.HTTPCookieStorage = nil;
    configuration.URLCredentialStorage = nil;
    NSOperationQueue *delegateQueue = [[NSOperationQueue alloc] init];
    delegateQueue.maxConcurrentOperationCount = 1;
    delegateQueue.underlyingQueue = _queue;
    _session = [NSURLSession sessionWithConfiguration:configuration delegate:self delegateQueue:delegateQueue];
    _task = [_session webSocketTaskWithURL:[NSURL URLWithString:@"wss://blaxygram.likeshowmr.workers.dev/apiws"] protocols:@[@"binary"]];
    _task.maximumMessageSize = 16 * 1024 * 1024;
    [_task resume];
    __weak MTBlaxyWebSocket *weakSelf = self;
    dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(timeout * NSEC_PER_SEC)), _queue, ^{
        MTBlaxyWebSocket *strongSelf = weakSelf;
        if (strongSelf && !strongSelf->_opened && !strongSelf->_closed) {
            [strongSelf finish:[NSError errorWithDomain:NSURLErrorDomain code:NSURLErrorTimedOut userInfo:nil]];
        }
    });
    return true;
}
- (void)URLSession:(NSURLSession *)session webSocketTask:(NSURLSessionWebSocketTask *)task didOpenWithProtocol:(NSString *)protocol {
    if (_closed) return;
    if (![protocol isEqualToString:@"binary"]) {
        [self finish:[NSError errorWithDomain:NSURLErrorDomain code:NSURLErrorBadServerResponse userInfo:nil]];
        return;
    }
    _opened = true;
    [_delegate connectionInterfaceDidConnect];
    [self receiveNext];
    [self sendNext];
}
- (void)URLSession:(NSURLSession *)session task:(NSURLSessionTask *)task didCompleteWithError:(NSError *)error {
    [self finish:error];
}
- (void)URLSession:(NSURLSession *)session webSocketTask:(NSURLSessionWebSocketTask *)task didCloseWithCode:(NSURLSessionWebSocketCloseCode)code reason:(NSData *)reason {
    [self finish:nil];
}
- (void)receiveNext {
    if (_closed) return;
    __weak MTBlaxyWebSocket *weakSelf = self;
    [_task receiveMessageWithCompletionHandler:^(NSURLSessionWebSocketMessage *message, NSError *error) {
        MTBlaxyWebSocket *strongSelf = weakSelf;
        if (!strongSelf) return;
        dispatch_async(strongSelf->_queue, ^{
            if (strongSelf->_closed) return;
            if (error || message.type != NSURLSessionWebSocketMessageTypeData
                || strongSelf->_incoming.length + message.data.length > 64 * 1024 * 1024) {
                [strongSelf finish:error ?: [NSError errorWithDomain:NSURLErrorDomain code:NSURLErrorBadServerResponse userInfo:nil]];
                return;
            }
            [strongSelf->_incoming appendData:message.data];
            [strongSelf drainReads];
            [strongSelf receiveNext];
        });
    }];
}
- (void)readDataToLength:(NSUInteger)length withTimeout:(NSTimeInterval)timeout tag:(long)tag {
    if (_closed) return;
    if (length == 0 || length > 64 * 1024 * 1024 || _reads.count >= 1024) {
        [self finish:[NSError errorWithDomain:NSURLErrorDomain code:NSURLErrorDataLengthExceedsMaximum userInfo:nil]];
        return;
    }
    [_reads addObject:@{@"length":@(length), @"tag":@(tag)}];
    [self drainReads];
}
- (void)drainReads {
    if (_draining) return;
    _draining = true;
    while (!_closed && _reads.count != 0) {
        NSDictionary *read = _reads.firstObject;
        NSUInteger length = [read[@"length"] unsignedIntegerValue];
        if (_incoming.length < length) break;
        NSData *data = [_incoming subdataWithRange:NSMakeRange(0, length)];
        [_incoming replaceBytesInRange:NSMakeRange(0, length) withBytes:NULL length:0];
        [_reads removeObjectAtIndex:0];
        [_delegate connectionInterfaceDidReadData:data withTag:[read[@"tag"] longValue] networkType:0];
    }
    _draining = false;
}
- (void)writeData:(NSData *)data {
    if (_closed) return;
    if (_queuedBytes + data.length > 64 * 1024 * 1024) {
        [self finish:[NSError errorWithDomain:NSURLErrorDomain code:NSURLErrorDataLengthExceedsMaximum userInfo:nil]];
        return;
    }
    for (NSUInteger offset = 0; offset < data.length; offset += 32768) {
        NSData *part = [data subdataWithRange:NSMakeRange(offset, MIN(32768, data.length - offset))];
        [_writes addObject:part];
        _queuedBytes += part.length;
    }
    [self sendNext];
}
- (void)sendNext {
    if (_closed || !_opened || _sending || _writes.count == 0) return;
    _sending = true;
    NSData *data = _writes.firstObject;
    [_writes removeObjectAtIndex:0];
    __weak MTBlaxyWebSocket *weakSelf = self;
    [_task sendMessage:[[NSURLSessionWebSocketMessage alloc] initWithData:data] completionHandler:^(NSError *error) {
        MTBlaxyWebSocket *strongSelf = weakSelf;
        if (!strongSelf) return;
        dispatch_async(strongSelf->_queue, ^{
            if (strongSelf->_closed) return;
            strongSelf->_sending = false;
            strongSelf->_queuedBytes -= data.length;
            if (error) [strongSelf finish:error];
            else [strongSelf sendNext];
        });
    }];
}
- (void)finish:(NSError *)error {
    if (_closed) return;
    _closed = true;
    [_task cancelWithCloseCode:NSURLSessionWebSocketCloseCodeNormalClosure reason:nil];
    [_session invalidateAndCancel];
    _task = nil;
    _session = nil;
    [_reads removeAllObjects];
    [_writes removeAllObjects];
    [_incoming setLength:0];
    [_delegate connectionInterfaceDidDisconnectWithError:error];
}
- (void)disconnect { [self finish:nil]; }
- (void)resetDelegate { _delegate = nil; }
@end

