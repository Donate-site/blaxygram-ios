"""Direct discussion pricing from channel settings, with acknowledged saves."""
from paid_messages import patch

PATHS = [
    'submodules/TelegramUI/Components/PeerInfo/PeerInfoScreen/Sources/PeerInfoInteraction.swift',
    'submodules/TelegramUI/Components/PeerInfo/PeerInfoScreen/Sources/PeerInfoScreen.swift',
    'submodules/TelegramUI/Components/PeerInfo/PeerInfoScreen/Sources/PeerInfoProfileItems.swift',
    'submodules/TelegramUI/Components/PeerInfo/PostSuggestionsSettingsScreen/Sources/PostSuggestionsSettingsScreen.swift',
    'submodules/TelegramCore/Sources/State/PaidMessages.swift',
    'submodules/TelegramCore/Sources/TelegramEngine/Peers/TelegramEnginePeers.swift',
]

def prepare_channel_comments(root):
    interaction, screen, items, settings, core, engine = [root / p for p in PATHS]
    patch(interaction, '    let editingOpenPostSuggestionsSetup: () -> Void',
          '    let editingOpenPaidCommentsSetup: () -> Void\n    let editingOpenPostSuggestionsSetup: () -> Void')
    patch(interaction, '        editingOpenPostSuggestionsSetup: @escaping () -> Void,',
          '        editingOpenPaidCommentsSetup: @escaping () -> Void,\n        editingOpenPostSuggestionsSetup: @escaping () -> Void,')
    patch(interaction, '        self.editingOpenPostSuggestionsSetup = editingOpenPostSuggestionsSetup',
          '        self.editingOpenPaidCommentsSetup = editingOpenPaidCommentsSetup\n        self.editingOpenPostSuggestionsSetup = editingOpenPostSuggestionsSetup')
    patch(screen, '            editingOpenPostSuggestionsSetup: { [weak self] in', '''            editingOpenPaidCommentsSetup: { [weak self] in
                self?.editingOpenPaidCommentsSetup()
            },
            editingOpenPostSuggestionsSetup: { [weak self] in''')
    patch(screen, '    private func editingOpenPostSuggestionsSetup() {', '''    private func editingOpenPaidCommentsSetup() {
        guard let data = self.data else { return }
        guard let discussion = data.linkedDiscussionPeer else {
            self.editingOpenDiscussionGroupSetup()
            return
        }
        guard case let .channel(group) = discussion, group.hasPermission(.banMembers) else {
            self.controller?.present(textAlertController(context: self.context, title: nil, text: self.presentationData.strings.Blaxy_CommentsPermission, actions: [TextAlertAction(type: .defaultAction, title: self.presentationData.strings.Common_OK, action: {})]), in: .window(.root))
            return
        }
        if #available(iOS 13.0, *) {
            let context = self.context
            Task { @MainActor [weak self] in
                let settings = await context.sharedContext.makePostSuggestionsSettingsScreen(context: context, peerId: discussion.id)
                self?.controller?.push(settings)
            }
        }
    }

    private func editingOpenPostSuggestionsSetup() {''')
    patch(items, '                let ItemPeerAutoTranslate = 15', '                let ItemPeerAutoTranslate = 15\n                let ItemPaidComments = 16')
    marker = '                    items[.peerSettings]!.append(PeerInfoScreenDisclosureItem(id: ItemPostSuggestionsSettings,'
    patch(items, marker, '''                    let commentsLabel: String
                    if case let .channel(group) = data.linkedDiscussionPeer {
                        let amount = group.sendPaidMessageStars?.value ?? 0
                        commentsLabel = amount > 0 ? "⭐ \\(amount)" : presentationData.strings.PeerInfo_AllowChannelMessages_Free
                    } else {
                        commentsLabel = presentationData.strings.Channel_DiscussionGroupAdd
                    }
                    items[.peerSettings]!.append(PeerInfoScreenDisclosureItem(id: ItemPaidComments, label: .text(commentsLabel), text: presentationData.strings.Blaxy_PaidComments, icon: PresentationResourcesSettings.chatHistory, action: {
                        interaction.editingOpenPaidCommentsSetup()
                    }))

''' + marker)
    patch(settings, '\n    let initialPrice: StarsAmount?', '''
    var isComments: Bool {
        if case let .channel(channel) = self.peer, case .group = channel.info { return true }
        return false
    }
    let initialPrice: StarsAmount?''')
    patch(settings, '        private var isUpdating: Bool = false', '''        private var isUpdating: Bool = false
        private var isSaving = false
        private var didSave = false
        private let saveDisposable = MetaDisposable()''')
    patch(settings, '        deinit {\n        }', '        deinit {\n            self.saveDisposable.dispose()\n        }')
    patch(settings, '''            if component.initialPrice != currentAmount {
                let _ = component.context.engine.peers.updateChannelPaidMessagesStars(peerId: peer.id, stars: currentAmount, broadcastMessagesAllowed: currentAmount != nil).startStandalone()
            }
            
            return true''', '''            if self.didSave || component.initialPrice == currentAmount { return true }
            if self.isSaving { return false }
            self.isSaving = true
            self.isUserInteractionEnabled = false
            self.saveDisposable.set((component.context.engine.peers.updateChannelPaidMessagesStarsChecked(peerId: peer.id, stars: currentAmount, broadcastMessagesAllowed: !component.isComments && currentAmount != nil)
            |> deliverOnMainQueue).start(error: { [weak self] _ in
                guard let self else { return }
                self.isSaving = false
                self.isUserInteractionEnabled = true
                let data = component.context.sharedContext.currentPresentationData.with { $0 }
                self.environment?.controller()?.present(textAlertController(context: component.context, title: nil, text: data.strings.Blaxy_PriceSaveError, actions: [TextAlertAction(type: .defaultAction, title: data.strings.Common_OK, action: {})]), in: .window(.root))
            }, completed: { [weak self] in
                guard let self else { return }
                self.isSaving = false
                self.isUserInteractionEnabled = true
                self.didSave = true
                complete()
            }))
            return false''')
    patch(settings, 'self.areSuggestionsEnabled = true', 'self.areSuggestionsEnabled = !component.isComments || initialPrice.value > 0')
    patch(settings, 'string: environment.strings.ChannelMessages_Title,', 'string: component.isComments ? environment.strings.Blaxy_PaidComments : environment.strings.ChannelMessages_Title,')
    patch(settings, 'parseMarkdownIntoAttributedString(environment.strings.ChannelMessages_Info,', 'parseMarkdownIntoAttributedString(component.isComments ? environment.strings.Blaxy_CommentsInfo : environment.strings.ChannelMessages_Info,')
    patch(settings, 'string: environment.strings.ChannelMessages_SwitchTitle,', 'string: component.isComments ? environment.strings.Blaxy_CommentsSwitch : environment.strings.ChannelMessages_SwitchTitle,')
    patch(settings, 'string: environment.strings.ChannelMessages_PriceSectionTitle,', 'string: component.isComments ? environment.strings.Blaxy_CommentPrice : environment.strings.ChannelMessages_PriceSectionTitle,')
    patch(settings, 'self.areSuggestionsEnabled && !address.isEmpty', '!component.isComments && self.areSuggestionsEnabled && !address.isEmpty', expected=2)
    patch(settings, '        self.navigationItem.backBarButtonItem =', '        self.navigationItem.rightBarButtonItem = UIBarButtonItem(title: presentationData.strings.Common_Save, style: .done, target: self, action: #selector(self.savePressed))\n        self.navigationItem.backBarButtonItem =')
    patch(settings, '    @objc private func cancelPressed() {', '''    @objc private func savePressed() {
        guard let view = self.node.hostView.componentView as? PostSuggestionsSettingsScreenComponent.View else { return }
        let close: () -> Void = { [weak self] in
            _ = self?.navigationController?.popViewController(animated: true)
        }
        if view.attemptNavigation(complete: close) { close() }
    }

    @objc private func cancelPressed() {''')
    patch(settings, 'if !transition.animation.isImmediate {', 'if !transition.animation.isImmediate && !UIAccessibility.isReduceMotionEnabled {')
    patch(settings, 'self.state?.updated(transition: .spring(duration: 0.4))', 'self.state?.updated(transition: UIAccessibility.isReduceMotionEnabled ? .immediate : .spring(duration: 0.4))')
    patch(engine, '        public func updateChannelPaidMessagesStars(peerId:', '''        public func updateChannelPaidMessagesStarsChecked(peerId: EnginePeer.Id, stars: StarsAmount?, broadcastMessagesAllowed: Bool) -> Signal<Never, UpdateChannelPaidMessagesError> {
            return _internal_updateChannelPaidMessagesStarsChecked(account: self.account, peerId: peerId, stars: stars, broadcastMessagesAllowed: broadcastMessagesAllowed)
        }

        public func updateChannelPaidMessagesStars(peerId:''')
    patch(core, 'public final class PostponeSendPaidMessageAction:', '''public enum UpdateChannelPaidMessagesError {
    case generic
}

func _internal_updateChannelPaidMessagesStarsChecked(account: Account, peerId: PeerId, stars: StarsAmount?, broadcastMessagesAllowed: Bool) -> Signal<Never, UpdateChannelPaidMessagesError> {
    return account.postbox.transaction { transaction -> Api.InputChannel? in
        return transaction.getPeer(peerId).flatMap(apiInputChannel)
    }
    |> castError(UpdateChannelPaidMessagesError.self)
    |> mapToSignal { inputChannel -> Signal<Never, UpdateChannelPaidMessagesError> in
        guard let inputChannel else { return .fail(.generic) }
        return account.network.request(Api.functions.channels.updatePaidMessagesPrice(flags: broadcastMessagesAllowed ? 1 : 0, channel: inputChannel, sendPaidMessagesStars: stars?.value ?? 0))
        |> mapError { _ in UpdateChannelPaidMessagesError.generic }
        |> mapToSignal { updates -> Signal<Never, UpdateChannelPaidMessagesError> in
            account.stateManager.addUpdates(updates)
            return account.postbox.transaction { transaction -> Void in
                guard let channel = transaction.getPeer(peerId) as? TelegramChannel else { return }
                switch channel.info {
                case .group:
                    transaction.updatePeersInternal([channel.withUpdatedSendPaidMessageStars(stars)], update: { _, peer in peer })
                case let .broadcast(info):
                    var flags = info.flags
                    if broadcastMessagesAllowed { flags.insert(.hasMonoforum) }
                    else { flags.remove(.hasMonoforum) }
                    transaction.updatePeersInternal([channel.withUpdatedInfo(.broadcast(TelegramChannelBroadcastInfo(flags: flags)))], update: { _, peer in peer })
                    if let linkedId = channel.linkedMonoforumId, let linked = transaction.getPeer(linkedId) as? TelegramChannel {
                        transaction.updatePeersInternal([linked.withUpdatedSendPaidMessageStars(stars)], update: { _, peer in peer })
                    }
                }
            }
            |> castError(UpdateChannelPaidMessagesError.self)
            |> ignoreValues
        }
    }
}

public final class PostponeSendPaidMessageAction:''')
    strings = root / 'Telegram/Telegram-iOS/en.lproj/Localizable.strings'
    with strings.open('a', encoding='utf-8', newline='\n') as f:
        f.write('''
"Blaxy.PaidComments" = "Платные комментарии";
"Blaxy.CommentsInfo" = "Цена действует на комментарии и сообщения в связанной группе обсуждений. Администраторы пишут бесплатно. У сообщений каналу отдельная цена. Укажите 0, чтобы отключить оплату.";
"Blaxy.CommentsSwitch" = "Оплата комментариев звёздами";
"Blaxy.CommentPrice" = "ЦЕНА ОДНОГО КОММЕНТАРИЯ";
"Blaxy.CommentsPermission" = "Нужно право блокировать участников в группе обсуждений.";
"Blaxy.PriceSaveError" = "Не удалось сохранить цену. Проверьте соединение и права администратора, затем попробуйте снова.";
''')
