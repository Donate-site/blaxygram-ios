"""Keep Blaxygram's paid-message settings visible and refresh their live state."""

def patch(path, old, new, expected=1):
    source = path.read_text(encoding='utf-8')
    if source.count(old) != expected:
        raise RuntimeError(f'Unexpected paid-message source shape: {path}')
    path.write_text(source.replace(old, new), encoding='utf-8', newline='\n')


def prepare_paid_messages(root):
    account = root / 'submodules/AccountContext/Sources/AccountContext.swift'
    # This is a native Blaxygram capability; an empty/old cache must not hide it.
    # An explicit server false still disables the option.
    patch(account, '            paidMessagesAvailable: false,',
          '            paidMessagesAvailable: true,')

    screen = root / 'submodules/SettingsUI/Sources/Privacy and Security/IncomingMessagePrivacyScreen.swift'
    patch(screen,
          '    let configuration = StarsSubscriptionConfiguration.with(appConfiguration: context.currentAppConfiguration.with { $0 })',
          '    var configuration = StarsSubscriptionConfiguration.with(appConfiguration: context.currentAppConfiguration.with { $0 })')
    patch(screen,
          '        statePromise.get(),\n        enableSetting\n    )\n    |> map { presentationData, state, enableSetting -> (ItemListControllerState, (ItemListNodeState, Any)) in',
          '        statePromise.get(),\n        enableSetting,\n'
          '        context.engine.data.subscribe(TelegramEngine.EngineData.Item.Configuration.App()),\n'
          '        context.engine.data.subscribe(TelegramEngine.EngineData.Item.Peer.Peer(id: context.account.peerId))\n'
          '    )\n    |> map { presentationData, state, enableSetting, appConfiguration, accountPeer -> (ItemListControllerState, (ItemListNodeState, Any)) in\n'
          '        configuration = StarsSubscriptionConfiguration.with(appConfiguration: appConfiguration)')
    patch(screen,
          'enableSetting: enableSetting, isPremium: context.isPremium, configuration: configuration)',
          'enableSetting: enableSetting, isPremium: accountPeer?.isPremium ?? false, configuration: configuration)')

    privacy = root / 'submodules/SettingsUI/Sources/Privacy and Security/PrivacyAndSecurityController.swift'
    source = privacy.read_text(encoding='utf-8')
    begin = source.index('        if !isPremiumDisabled || isPremium {\n            entries.append(.voiceMessagePrivacy')
    end = source.index('        entries.append(.groupPrivacy(', begin)
    block = source[begin:end]
    first, rest = block.split('            var effectiveValue', 1)
    assert rest.endswith('        }\n')
    rest = '            var effectiveValue' + rest[:-10]
    rest = '\n'.join(line[4:] if line.startswith('    ') else line for line in rest.split('\n'))
    source = source[:begin] + first + '        }\n' + rest + source[end:]
    privacy.write_text(source, encoding='utf-8', newline='\n')
    patch(privacy,
          '            entries.append(.messagePrivacy(presentationData.theme, presentationData.strings.Channel_NotificationLoading, isPremium))\n        }',
          '        }\n        entries.append(.messagePrivacy(presentationData.theme, presentationData.strings.Channel_NotificationLoading, isPremium))')
