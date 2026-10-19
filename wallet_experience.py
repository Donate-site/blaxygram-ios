"""Native receive card and Blaxygram wallet/collectible deep links."""
from paid_messages import patch
import shutil

BALANCE = 'submodules/TelegramUI/Components/Stars/StarsTransactionsScreen/Sources/StarsBalanceComponent.swift'
OPEN_URL = 'submodules/TelegramUI/Sources/OpenUrl.swift'
PATHS = [OPEN_URL]

def prepare_wallet_experience(root, assets):
    destination = root / BALANCE
    shutil.copyfile(assets / 'GramReceiveController.swift', destination.parent / 'GramReceiveController.swift')
    patch(destination, '            self.gramCard.addSubview(self.gramQr)', '''            self.gramCard.addSubview(self.gramQr)
            self.gramCard.addGestureRecognizer(UITapGestureRecognizer(target: self, action: #selector(self.openGramReceive)))
            self.gramCard.isAccessibilityElement = true
            self.gramCard.accessibilityLabel = "Кошелёк GRAM. Показать QR и адрес"''')
    patch(destination, '        required init?(coder: NSCoder) {', '''        @objc private func openGramReceive() {
            guard let component = self.component, let address = component.walletId,
                  component.currency == .ton, var presenter = self.window?.rootViewController else { return }
            while let next = presenter.presentedViewController { presenter = next }
            presenter.present(GramReceiveController(address: address, theme: component.theme, topUp: component.action), animated: true)
        }

        required init?(coder: NSCoder) {''')
    patch(destination, 'self.gramId.text = "BLX-DEMO · " + String((component.walletId ?? "").suffix(8))', 'self.gramId.text = "Мой кошелёк GRAM"')
    patch(destination, 'self.gramAmount.text = formattedLabel + " GRAM"', 'self.gramAmount.text = "💎 " + formattedLabel + " GRAM"')
    patch(root / 'Telegram/BUILD', '                <string>tonsite</string>', '                <string>tonsite</string>\n                <string>owpg</string>')
    app = root / 'submodules/TelegramUI/Sources/AppDelegate.swift'
    patch(app, 'url.scheme == "tg" || url.scheme == buildConfig.appSpecificUrlScheme {', 'url.scheme == "tg" || url.scheme == "owpg" || url.scheme == buildConfig.appSpecificUrlScheme {')
    patch(app, 'urlString.lowercased().hasPrefix("tg:") || urlString.lowercased().hasPrefix("\\(buildConfig.appSpecificUrlScheme):")', 'urlString.lowercased().hasPrefix("tg:") || urlString.lowercased().hasPrefix("owpg:") || urlString.lowercased().hasPrefix("\\(buildConfig.appSpecificUrlScheme):")')
    opening = 'func openExternalUrlImpl(context: AccountContext, urlContext: OpenURLContext, url: String, forceExternal: Bool, presentationData: PresentationData, navigationController: NavigationController?, dismissInput: @escaping () -> Void) {'
    patch(root / OPEN_URL, opening, opening + '''
    // Handle Blaxygram links before external-browser preferences, on our own account.
    if let parts = URLComponents(string: url) {
        let scheme = (parts.scheme ?? "").lowercased()
        let host = (parts.host ?? "").lowercased()
        let ownScheme = ["blaxygram", "owpg"].contains(scheme)
        let ownHost = ["blaxygram.duckdns.org", "web.blaxygram.duckdns.org", "blaxygment.blaxygram.duckdns.org"].contains(host)
        let ownHttps = scheme == "https" && ownHost
        let query = parts.queryItems ?? []
        if ownScheme || ownHttps {
            let address = query.first(where: { $0.name == "address" || $0.name == "gram" })?.value
                ?? (parts.path == "/mini/gram-link.html" ? parts.fragment : nil)
            if let address = address, address.range(of: "^BLX-DEMO-[A-F0-9]{36}$", options: .regularExpression) != nil {
                dismissInput()
                context.sharedContext.presentGlobalController(textAlertController(context: context,
                    title: "Что хотите сделать?", text: "Кошелёк получателя:\\n" + address,
                    actions: [
                        TextAlertAction(type: .defaultAction, title: "Отправить", action: {
                            context.sharedContext.applicationBindings.openUrl("https://t.me/blaxxgrambot?start=bg_send_" + String(address.dropFirst(9)))
                        }),
                        TextAlertAction(type: .genericAction, title: "Закрыть", action: {})
                    ], parseMarkdown: false), nil)
                return
            }
            let path = parts.path.split(separator: "/").map(String.init)
            var slug: String?
            if ownScheme && (host == "nft" || path.first == "nft") {
                slug = query.first(where: { $0.name == "slug" })?.value
            }
            if path.count == 2 && path[0] == "nft" { slug = path[1] }
            if let slug = slug, slug.range(of: "^[A-Za-z0-9_-]{1,128}$", options: .regularExpression) != nil {
                let handler = makeResolvedUrlHandler(context: context, presentationData: presentationData,
                    navigationController: navigationController, dismissInput: dismissInput)
                makeInternalUrlHandler(context: context, resolvedHandler: handler)("https://t.me/nft/" + slug)
                return
            }
            // A launcher link simply reveals the app; do not resolve "mtproto" as a username.
            if (ownScheme && host == "mtproto" && path.isEmpty) || (ownHttps && parts.path == "/mtproto/") {
                return
            }
        }
    }
''')
