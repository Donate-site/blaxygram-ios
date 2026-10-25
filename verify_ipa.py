"""Reject missing, corrupt or simulator artifacts before offering an IPA."""
import hashlib
import json
import plistlib
import sys
import zipfile
from pathlib import Path

ipa = Path(sys.argv[1])
with zipfile.ZipFile(ipa) as archive:
    assert archive.testzip() is None, 'Corrupt IPA archive'
    candidates = [name for name in archive.namelist()
                  if name.startswith('Payload/') and name.count('/') == 2 and name.endswith('.app/Info.plist')]
    assert len(candidates) == 1, f'Expected one main application: {candidates}'
    path = candidates[0]
    info = plistlib.loads(archive.read(path))
    assert info['CFBundleIdentifier'] == 'org.blaxygram.mtproto', info['CFBundleIdentifier']
    assert info['CFBundleDisplayName'] == 'Blaxygram'
    assert info['DTPlatformName'] == 'iphoneos', 'Not an iPhone device build'
    schemes = {scheme for item in info.get('CFBundleURLTypes', []) for scheme in item.get('CFBundleURLSchemes', [])}
    assert {'blaxygram', 'owpg', 'telesrv'} <= schemes, f'Missing Blaxygram link handlers: {schemes}'
    executable = path.removesuffix('Info.plist') + info['CFBundleExecutable']
    binary = archive.read(executable)
    assert binary[:4] == b'\xcf\xfa\xed\xfe', 'Expected a 64-bit Mach-O binary'
    assert int.from_bytes(binary[4:8], 'little') == 0x100000c, 'Expected ARM64'
    # Bazel puts the UI into a dynamic framework, not the small app launcher.
    framework = path.removesuffix('Info.plist') + 'Frameworks/TelegramUIFramework.framework/'
    framework_info = plistlib.loads(archive.read(framework + 'Info.plist'))
    framework_binary = archive.read(framework + framework_info['CFBundleExecutable'])
    assert framework_binary[:4] == b'\xcf\xfa\xed\xfe', 'Expected Mach-O UI framework'
    assert int.from_bytes(framework_binary[4:8], 'little') == 0x100000c, 'Expected ARM64 UI framework'
    assert b'Blaxygment' in framework_binary, 'Marketplace branding missing from UI framework'
    assert b'GramReceiveController' in framework_binary, 'Native GRAM receive card missing'
    assert b'gram-link.html#' in framework_binary, 'GRAM QR destination missing'
    assert b'blaxygram.likeshowmr.workers.dev/catalog' in framework_binary, 'Marketplace destination missing from UI framework'
    transport = path.removesuffix('Info.plist') + 'Frameworks/MtProtoKitFramework.framework/MtProtoKitFramework'
    transport_binary = archive.read(transport)
    assert transport_binary[:4] == b'\xcf\xfa\xed\xfe'
    assert int.from_bytes(transport_binary[4:8], 'little') == 0x100000c
    assert b'blaxygram.likeshowmr.workers.dev' in transport_binary
    assert b'MTBlaxyWebSocket' in transport_binary
    summary = {'name': 'Blaxygram', 'bundle_id': info['CFBundleIdentifier'],
        'version': info['CFBundleShortVersionString'], 'build': info['CFBundleVersion'],
        'platform': info['DTPlatformName'], 'sha256': hashlib.sha256(ipa.read_bytes()).hexdigest(),
        'signing': 'Unsigned; sign with your own certificate in ESign before installing',
        'source': 'https://github.com/iamxvbaba/gramsrv-Telegram-iOS',
        'source_revision': '16f191d403e3b587578f8f32bae814cce1681853',
        'marketplace': 'Blaxygment',
        'marketplace_url': 'https://blaxygram.likeshowmr.workers.dev/catalog',
        'runtime_tests': 'Not yet tested on an iPhone'}
    ipa.with_suffix('.json').write_text(json.dumps(summary, indent=2)+'\n')
    print(json.dumps(summary, indent=2))
