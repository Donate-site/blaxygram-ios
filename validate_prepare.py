"""Validate patches against pristine pinned sources; does not compile an IPA."""
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import prepare

source = Path(sys.argv[1]).resolve()
assets = Path(__file__).resolve().parent
root = Path(tempfile.mkdtemp(prefix='blaxygram-ios-market-check-'))
subprocess.run(['git', 'clone', '--shared', '--no-checkout', '--quiet', str(source), str(root)], check=True)
paths = [
    '.bazelrc', 'Telegram/BUILD',
    'Telegram/Telegram-iOS/en.lproj/InfoPlist.strings',
    'Telegram/Telegram-iOS/en.lproj/Localizable.strings',
    'build-system/GenerateStrings/GenerateStrings.py',
    'submodules/TelegramCore/Sources/Network/Network.swift',
    'submodules/MtProtoKit/Sources/MTDatacenterAuthMessageService.m',
    'submodules/MtProtoKit/Sources/MTContext.m',
    'submodules/TelegramUI/Sources/AppDelegate.swift',
    'submodules/AuthorizationUI/Sources/AuthorizationSequenceCodeEntryControllerNode.swift',
    'submodules/TelegramUI/Components/Settings/CollectibleItemInfoScreen/Sources/CollectibleItemInfoScreen.swift',
    'submodules/TelegramUI/Components/Stars/StarsAvatarComponent/Sources/StarsAvatarComponent.swift',
    'submodules/TelegramUI/Components/Stars/StarsImageComponent/Sources/StarsImageComponent.swift',
    'submodules/TelegramUI/Images.xcassets/Premium/Stars/Fragment.imageset/Contents.json',
    'submodules/TelegramUI/Images.xcassets/Premium/Stars/Fragment.imageset/fragment.pdf',
    'submodules/UrlWhitelist/Sources/UrlWhitelist.swift',
    'submodules/TextFormat/Sources/GenerateTextEntities.swift',
    'submodules/StatisticsUI/Sources/TransactionInfoScreen.swift',
]
subprocess.run(['git', '-C', str(root), 'checkout', prepare.SOURCE_REVISION, '--', *paths], check=True)
rules = Path('build-system/bazel-rules/rules_apple')
target = root / rules / 'apple/internal/ios_rules.bzl'
target.parent.mkdir(parents=True, exist_ok=True)
target.write_bytes(subprocess.check_output(['git', '-C', str(source / rules), 'show', 'HEAD:apple/internal/ios_rules.bzl']))
real_run = subprocess.run


def local_run(args, **kwargs):
    if args[0] == 'sips':
        # Only macOS image resizing is unavailable; preserve the real asset.
        return subprocess.CompletedProcess(args, 0)
    return real_run(args, **kwargs)


with patch.object(prepare.subprocess, 'run', side_effect=local_run):
    prepare.prepare(root, assets)

localization = root / 'Telegram/Telegram-iOS/en.lproj/Localizable.strings'
subprocess.run([sys.executable, str(root / 'build-system/GenerateStrings/GenerateStrings.py'),
    '--source', str(localization), '--outImplementation', str(root / 'PresentationStrings.m'),
    '--outHeader', str(root / 'PresentationStrings.h'), '--outData', str(root / 'PresentationStrings.data')], check=True)
generated = (root / 'PresentationStrings.m').read_text(encoding='utf-8')
assert 'withTemplate:@"Blaxygment"' in generated
assert generated.index('marketNamePattern =') < generated.index('static NSString * _Nonnull getSingleIndirect')
assert '"Login.OpenFragment" = "Open Blaxygment";' in localization.read_text(encoding='utf-8')
assert 'Withdrawal("Blaxygment")' in (root / 'submodules/StatisticsUI/Sources/TransactionInfoScreen.swift').read_text(encoding='utf-8')
icon = root / 'submodules/TelegramUI/Images.xcassets/Premium/Stars/Fragment.imageset'
assert (icon / 'Blaxygment.png').read_bytes() == (assets / 'Blaxygment.png').read_bytes()
assert json.loads((icon / 'Contents.json').read_text())['images'][0]['filename'] == 'Blaxygment.png'
assert {p.name for p in icon.iterdir()} == {'Contents.json', 'Blaxygment.png'}, 'Unassigned asset in image set'
assert '"fragment.com"' not in (root / 'submodules/UrlWhitelist/Sources/UrlWhitelist.swift').read_text()
report = {
    'source_revision': prepare.SOURCE_REVISION,
    'patch_application': 'PASS against pristine pinned source',
    'marketplace': 'Blaxygment',
    'host': 'blaxygment.blaxygram.duckdns.org',
    'generated_localizations': 'PASS; raw templates before interpolation',
    'market_avatar_sha256': hashlib.sha256((assets / 'Blaxygment.png').read_bytes()).hexdigest(),
    'server': '193.233.230.31:2398',
    'compile_status': 'Not run; requires GitHub macOS runner',
    'macos_icon_resize': 'Skipped on Windows',
    'device_tested': False,
    'test_tree': str(root),
}
(assets / 'prepare-validation.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(report, indent=2))
