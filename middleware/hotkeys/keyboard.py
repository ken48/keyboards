from Quartz import (
    CGEventCreateKeyboardEvent,
    CGEventPost,
    kCGEventSourceStateHIDSystemState,
    kCGHIDEventTap,
    CGEventSetFlags,
    CGEventCreate,
    CGEventSetIntegerValueField,
    kCGKeyboardEventKeycode,
    kCGEventKeyDown,
    kCGEventKeyUp
)


class FastKeyboard:
    def __init__(self):
        self.key_codes = {
            'a': 0,
            'c': 8,
            'v': 9,
            'left': 123
        }

        self.modifiers = {
            'sft': 0x20000,
            'ctl': 0x40000,
            'opt': 0x80000,
            'cmd': 0x100000
        }

    def send_key(self, key_name, modifier_flags=0):
        if key_name in self.key_codes:
            key_code = self.key_codes[key_name]

            # Key down
            event_down = CGEventCreateKeyboardEvent(None, key_code, True)
            if modifier_flags:
                CGEventSetFlags(event_down, modifier_flags)
            CGEventPost(kCGHIDEventTap, event_down)

            # Key up
            event_up = CGEventCreateKeyboardEvent(None, key_code, False)
            if modifier_flags:
                CGEventSetFlags(event_up, modifier_flags)
            CGEventPost(kCGHIDEventTap, event_up)

    def send_copy(self):
        self.send_key('c', self.modifiers['cmd'])

    def send_paste(self):
        self.send_key('v', self.modifiers['cmd'])

    def send_select_all(self):
        self.send_key('a', self.modifiers['cmd'])

    def send_select_last_word(self):
        self.send_key('left', self.modifiers['sft'] | self.modifiers['opt'])
