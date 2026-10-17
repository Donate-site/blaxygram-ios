"""Coral native defaults and battery-aware animation; saved user themes remain intact."""
from paid_messages import patch

def prepare_interface(root):
    day=root/'submodules/TelegramPresentationData/Sources/DefaultDayPresentationTheme.swift'
    patch(day,'public let defaultDayAccentColor = UIColor(rgb: 0x0088ff)',
          'public let defaultDayAccentColor = UIColor(rgb: 0xc94b49)')
    patch(day,'UIColor(rgb: 0xe1ffc7)','UIColor(rgb: 0xffe2db)',expected=4)
    patch(day,'UIColor(rgb: 0x21c004)','UIColor(rgb: 0xb64b48)')
    patch(day,'    UIColor(rgb: 0xdbddbb),\n    UIColor(rgb: 0x6ba587),\n    UIColor(rgb: 0xd5d88d),\n    UIColor(rgb: 0x88b884)',
          '    UIColor(rgb: 0xf7ece8),\n    UIColor(rgb: 0xe9dff3),\n    UIColor(rgb: 0xfbe7de),\n    UIColor(rgb: 0xeee5f6)')
    night=root/'submodules/TelegramPresentationData/Sources/DefaultDarkPresentationTheme.swift'
    patch(night,'accentColor: UIColor(rgb: 0x3e88f7)','accentColor: UIColor(rgb: 0xff9b8c)')
    energy=root/'submodules/TelegramUIPreferences/Sources/MediaAutoDownloadSettings.swift'
    patch(energy,'            activationThreshold: 15,','            activationThreshold: 20,',expected=2)
    patch(energy,'            loopStickers: true,','            loopStickers: isCapable,')
    # UI strings are resolved before formatting, including downloaded language packs.
    generator=root/'build-system/GenerateStrings/GenerateStrings.py'
    patch(generator,'    NSString *result = nil;\n    if (strings) {','''    if ([key isEqualToString:@"Login.OpenFragment"]) {
        if (isFound) *isFound = true;
        return strings && strings.lc == 0x7275 ? @"Открыть бота Blaxygram" : @"Open Blaxygram Bot";
    }
    if ([key isEqualToString:@"Login.EnterCodeFragmentText"]) {
        if (isFound) *isFound = true;
        return strings && strings.lc == 0x7275 ? @"Код для **%@** отправлен в **@blaxxgrambot** в Telegram." : @"Check **@blaxxgrambot** in Telegram for the code for **%@**.";
    }
    NSString *result = nil;
    if (strings) {''')
