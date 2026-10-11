"""Brand public marketplace UI while preserving MTProto identifiers and user data."""
import json
import re
import shutil
import sys
from pathlib import Path

HOST = 'blaxygment.blaxygram.duckdns.org'


def edit(path, transform):
    old = path.read_text(encoding='utf-8-sig')
    new = transform(old)
    if new != old:
        path.write_text(new, encoding='utf-8', newline='\n')


def replace_once(path, old, new):
    def transform(text):
        if new in text:
            return text
        if text.count(old) != 1:
            raise RuntimeError(f'Unexpected marketplace source: {path}')
        return text.replace(old, new)
    edit(path, transform)


def prepare_market(root, assets):
    # Whitelisted hosts and hard-coded destinations, including login and wallet.
    for folder in (root / 'submodules', root / 'Telegram'):
        for path in folder.rglob('*'):
            if path.suffix not in ('.swift', '.m', '.strings'):
                continue
            if any(part in ('ThirdParty', 'Pods', 'build') for part in path.parts):
                continue
            def transform(text):
                text = text.replace('https://fragment.com', 'https://' + HOST)
                text = text.replace('"fragment.com"', '"' + HOST + '"')
                if path.suffix == '.swift':
                    text = text.replace('"Fragment"', '"Blaxygment"')
                if path.suffix == '.strings':
                    text = re.sub(r'(?m)^(\s*"[^"\n]+"\s*=\s*")(.*)(";\s*)$',
                        lambda m: m[1] + re.sub(r'\bFragment\b', 'Blaxygment', m[2]) + m[3], text)
                return text
            edit(path, transform)

    # Transform templates before argument interpolation/range calculation.
    # This also handles cached and downloaded language packs without touching
    # usernames, messages, or protocol/localization keys.
    generator = root / 'build-system/GenerateStrings/GenerateStrings.py'
    replace_once(generator, '    return result;\n}\n\nstatic NSString * _Nonnull getSingleIndirect', '''    if ([result containsString:@"Fragment"] || [result containsString:@"fragment.com"]) {
        result = [result stringByReplacingOccurrencesOfString:@"https://fragment.com" withString:@"https://blaxygment.blaxygram.duckdns.org"];
        static NSRegularExpression *marketNamePattern = nil;
        static dispatch_once_t marketOnceToken;
        dispatch_once(&marketOnceToken, ^{
            marketNamePattern = [NSRegularExpression regularExpressionWithPattern:@"(?<![A-Za-z0-9_])Fragment(?![A-Za-z0-9_])" options:0 error:nil];
        });
        result = [marketNamePattern stringByReplacingMatchesInString:result options:0 range:NSMakeRange(0, result.length) withTemplate:@"Blaxygment"];
    }
    return result;
}

static NSString * _Nonnull getSingleIndirect''')

    # Retain the resource key used by TL .fragment transaction variants.
    icon = root / 'submodules/TelegramUI/Images.xcassets/Premium/Stars/Fragment.imageset'
    shutil.copyfile(assets / 'Blaxygment.png', icon / 'Blaxygment.png')
    (icon / 'Contents.json').write_text(json.dumps({
        'images': [{'filename': 'Blaxygment.png', 'idiom': 'universal'}],
        'info': {'author': 'xcode', 'version': 1},
        'properties': {'template-rendering-intent': 'original'}
    }, indent=2) + '\n', encoding='utf-8')

    base = root / 'submodules/TelegramUI/Components'
    collectible = base / 'Settings/CollectibleItemInfoScreen/Sources/CollectibleItemInfoScreen.swift'
    replace_once(collectible, '        private let icon = ComponentView<Empty>()',
                 '        private let icon = UIImageView(image: UIImage(bundleImageName: "Premium/Stars/Fragment"))')
    def collectible_icon(text):
        if 'self.icon.layer.cornerRadius = iconBackgroundFrame.width / 2.0' in text:
            return text
        start = text.index('            let iconAnimationName: String')
        end = text.index('            let titleText = NSMutableAttributedString()', start)
        return text[:start] + '''            if self.icon.superview == nil {
                self.icon.contentMode = .scaleAspectFill
                self.icon.clipsToBounds = true
                self.icon.accessibilityLabel = "Blaxygment"
                self.addSubview(self.icon)
            }
            self.icon.layer.cornerRadius = iconBackgroundFrame.width / 2.0
            transition.setFrame(view: self.icon, frame: iconBackgroundFrame)

''' + text[end:]
    edit(collectible, collectible_icon)

    avatar = base / 'Stars/StarsAvatarComponent/Sources/StarsAvatarComponent.swift'
    replace_once(avatar,
        'self.iconView.image = UIImage(bundleImageName: "Premium/Stars/Fragment")\n                    iconOffset = 2.0',
        'self.iconView.image = UIImage(bundleImageName: "Premium/Stars/Fragment")\n                    iconInset = 0.0\n                    iconOffset = 0.0')
    replace_once(avatar,
        '            self.iconView.frame = CGRect(origin: .zero, size: size).insetBy(dx: iconInset, dy: iconInset).offsetBy(dx: 0.0, dy: iconOffset)',
        '            self.iconView.frame = CGRect(origin: .zero, size: size).insetBy(dx: iconInset, dy: iconInset).offsetBy(dx: 0.0, dy: iconOffset)\n            self.iconView.clipsToBounds = true\n            self.iconView.layer.cornerRadius = self.iconView.bounds.width / 2.0')
    image = base / 'Stars/StarsImageComponent/Sources/StarsImageComponent.swift'
    replace_once(image,
        'iconView.image = UIImage(bundleImageName: "Premium/Stars/Fragment")\n                        iconOffset = 5.0',
        'iconView.image = UIImage(bundleImageName: "Premium/Stars/Fragment")\n                        iconInset = 0.0\n                        iconOffset = 0.0')
    replace_once(image,
        '                    iconView.frame = imageFrame.insetBy(dx: iconInset, dy: iconInset).offsetBy(dx: 0.0, dy: iconOffset)',
        '                    iconView.frame = imageFrame.insetBy(dx: iconInset, dy: iconInset).offsetBy(dx: 0.0, dy: iconOffset)\n                    iconView.clipsToBounds = true\n                    iconView.layer.cornerRadius = iconView.bounds.width / 2.0')

    login = root / 'submodules/AuthorizationUI/Sources/AuthorizationSequenceCodeEntryControllerNode.swift'
    replace_once(login, 'animationName = "IntroFragment"', 'animationName = "IntroMessage" // Blaxygment code delivery')
    replace_once(login, 'self.proceedNode.animation = "anim_fragment"', 'self.proceedNode.animation = nil // No upstream marketplace logo')
    print('Prepared Blaxygment marketplace names, URLs, cached translations and avatars.')


if __name__ == '__main__':
    prepare_market(Path(sys.argv[1]).resolve(), Path(__file__).resolve().parent)
