from pathlib import Path

def prepare_cloudflare_transport(root, assets):
    path = root/'submodules/MtProtoKit/Sources/MTTcpConnection.m'
    source = path.read_text(encoding='utf-8')
    marker = '@interface MTGcdAsyncSocketTcpConnectionInterface:'
    assert source.count(marker) == 1 and '@interface MTBlaxyWebSocket:' not in source
    source = source.replace(marker, (assets/'MTBlaxyWebSocket.inc').read_text(encoding='utf-8')+'\n'+marker)
    old = '''            if (_makeTcpConnectionInterface) {
                _socket = _makeTcpConnectionInterface(self, [[MTTcpConnection tcpQueue] nativeQueue]);
            }'''
    new = '''            bool blaxyRoute = _socksIp == nil && _mtpIp == nil
                && _scheme.address.port == 2398
                && ([_scheme.address.ip isEqualToString:@"31.77.16.230"]
                    || [_scheme.address.ip isEqualToString:@"193.233.230.31"]);
            if (blaxyRoute) {
                _socket = [[MTBlaxyWebSocket alloc] initWithDelegate:self queue:[[MTTcpConnection tcpQueue] nativeQueue]];
            } else if (_makeTcpConnectionInterface) {
                _socket = _makeTcpConnectionInterface(self, [[MTTcpConnection tcpQueue] nativeQueue]);
            }'''
    assert source.count(old) == 1
    path.write_text(source.replace(old, new), encoding='utf-8', newline='\n')
