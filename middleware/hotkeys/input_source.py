# mac_input_source.py
import ctypes, ctypes.util
from ctypes import c_void_p, c_uint32, c_bool, c_long, c_char_p
from typing import Iterable, List, Optional, Dict

class MacInputSourceManager:
    CFStringRef       = c_void_p
    CFArrayRef        = c_void_p
    CFDictionaryRef   = c_void_p
    CFTypeRef         = c_void_p
    TISInputSourceRef = c_void_p
    kCFStringEncodingUTF8 = 0x08000100

    def __init__(self) -> None:
        self._CF = None
        self._HT = None
        self._T_LAYOUT = None
        self._T_INPUTMODE = None
        self._load_frameworks()
        self._bind_cf()
        self._bind_ht()
        self._load_cf_consts()

    @staticmethod
    def _load_framework(name: str, paths: Iterable[str]):
        lib = ctypes.util.find_library(name)
        if lib:
            try: return ctypes.CDLL(lib)
            except OSError: pass
        last = None
        for p in paths:
            try: return ctypes.CDLL(p)
            except OSError as e: last = e
        raise last or OSError(f"Cannot load framework {name}")

    def _load_frameworks(self):
        self._HT = self._load_framework("HIToolbox", [
            "/System/Library/Frameworks/Carbon.framework/Frameworks/HIToolbox.framework/HIToolbox",
            "/System/Library/Frameworks/ApplicationServices.framework/Frameworks/HIToolbox.framework/HIToolbox",
        ])
        self._CF = self._load_framework("CoreFoundation", [
            "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation",
        ])

    def _bind_cf(self):
        CF = self._CF
        CF.CFStringCreateWithCString.argtypes = [c_void_p, c_char_p, c_uint32]
        CF.CFStringCreateWithCString.restype  = self.CFStringRef

        CF.CFStringGetCString.argtypes = [self.CFStringRef, c_char_p, c_long, c_uint32]
        CF.CFStringGetCString.restype  = c_bool

        CF.CFArrayGetCount.argtypes = [self.CFArrayRef]
        CF.CFArrayGetCount.restype  = c_long

        CF.CFArrayGetValueAtIndex.argtypes = [self.CFArrayRef, c_long]
        CF.CFArrayGetValueAtIndex.restype  = c_void_p

        CF.CFRelease.argtypes = [c_void_p]
        CF.CFRelease.restype  = None

    def _bind_ht(self):
        HT = self._HT
        HT.TISCreateInputSourceList.argtypes  = [self.CFDictionaryRef, c_bool]
        HT.TISCreateInputSourceList.restype   = self.CFArrayRef
        HT.TISGetInputSourceProperty.argtypes = [self.TISInputSourceRef, c_void_p]
        HT.TISGetInputSourceProperty.restype  = self.CFTypeRef
        HT.TISSelectInputSource.argtypes      = [self.TISInputSourceRef]
        HT.TISSelectInputSource.restype       = c_uint32

    def _CFConst_optional(self, name: str) -> Optional[c_void_p]:
        try:
            return self.CFStringRef.in_dll(self._HT, name)
        except ValueError:
            return None

    def _load_cf_consts(self):
        # keys
        self.kTISPropertyInputSourceID         = self._CFConst_optional("kTISPropertyInputSourceID")
        self.kTISPropertyInputSourceType       = self._CFConst_optional("kTISPropertyInputSourceType")
        self.kTISPropertyLocalizedName         = self._CFConst_optional("kTISPropertyLocalizedName")
        self.kTISPropertyInputSourceIsSelected = self._CFConst_optional("kTISPropertyInputSourceIsSelected")
        # language keys (PrimaryLanguage may be absent on older systems)
        self.kTISPropertyPrimaryLanguage       = self._CFConst_optional("kTISPropertyPrimaryLanguage")
        self.kTISPropertyInputSourceLanguages  = self._CFConst_optional("kTISPropertyInputSourceLanguages")

        # types
        self.kTISTypeKeyboardLayout            = self._CFConst_optional("kTISTypeKeyboardLayout")
        self.kTISTypeKeyboardInputMode         = self._CFConst_optional("kTISTypeKeyboardInputMode")

        # canonical type strings for robust compare
        self._T_LAYOUT    = self._cfstring_to_py(self.kTISTypeKeyboardLayout) if self.kTISTypeKeyboardLayout else ""
        self._T_INPUTMODE = self._cfstring_to_py(self.kTISTypeKeyboardInputMode) if self.kTISTypeKeyboardInputMode else ""

    # utils
    def _cfstr(self, s: str) -> CFStringRef:
        return self._CF.CFStringCreateWithCString(None, s.encode("utf-8"), self.kCFStringEncodingUTF8)

    def _cfstring_to_py(self, cf: Optional[CFStringRef]) -> str:
        if not cf: return ""
        buf = ctypes.create_string_buffer(1024)
        ok = self._CF.CFStringGetCString(cf, buf, len(buf), self.kCFStringEncodingUTF8)
        return buf.value.decode("utf-8") if ok else ""

    def _create_input_source_array(self):
        return self._HT.TISCreateInputSourceList(None, True)

    def _read_lang(self, src) -> str:
        """Try InputSourceLanguages[0], fallback to PrimaryLanguage, else ''."""
        CF, HT = self._CF, self._HT
        # 1) array of languages
        if self.kTISPropertyInputSourceLanguages:
            langs_ref = HT.TISGetInputSourceProperty(src, self.kTISPropertyInputSourceLanguages)
            if langs_ref:
                arr = self.CFArrayRef(langs_ref)
                cnt = CF.CFArrayGetCount(arr)
                if cnt > 0:
                    first = self.CFStringRef(CF.CFArrayGetValueAtIndex(arr, 0))
                    s = self._cfstring_to_py(first)
                    if s:
                        return s
        # 2) primary language (may be absent)
        if self.kTISPropertyPrimaryLanguage:
            lang_ref = HT.TISGetInputSourceProperty(src, self.kTISPropertyPrimaryLanguage)
            if lang_ref:
                return self._cfstring_to_py(self.CFStringRef(lang_ref))
        return ""

    def list_sources(self, include_types: Optional[Iterable[str]] = ("layout", "inputmode")) -> List[Dict[str, str]]:
        arr = self._create_input_source_array()
        if not arr:
            raise RuntimeError("Не удалось получить список источников ввода")
        CF, HT = self._CF, self._HT
        out: List[Dict[str, str]] = []
        try:
            n = CF.CFArrayGetCount(arr)
            for i in range(n):
                src = self.TISInputSourceRef(CF.CFArrayGetValueAtIndex(arr, i))

                typ_ref  = HT.TISGetInputSourceProperty(src, self.kTISPropertyInputSourceType) if self.kTISPropertyInputSourceType else None
                name_ref = HT.TISGetInputSourceProperty(src, self.kTISPropertyLocalizedName)   if self.kTISPropertyLocalizedName else None
                id_ref   = HT.TISGetInputSourceProperty(src, self.kTISPropertyInputSourceID)    if self.kTISPropertyInputSourceID else None
                sel_ref  = HT.TISGetInputSourceProperty(src, self.kTISPropertyInputSourceIsSelected) if self.kTISPropertyInputSourceIsSelected else None

                typ_s  = self._cfstring_to_py(self.CFStringRef(typ_ref)) if typ_ref else ""
                name_s = self._cfstring_to_py(self.CFStringRef(name_ref)) if name_ref else ""
                id_s   = self._cfstring_to_py(self.CFStringRef(id_ref)) if id_ref else ""

                if   self._T_LAYOUT    and typ_s == self._T_LAYOUT:    human = "layout"
                elif self._T_INPUTMODE and typ_s == self._T_INPUTMODE: human = "inputmode"
                else:                                                   human = "other"

                if include_types and human not in include_types:
                    continue

                out.append({
                    "id": id_s,
                    "name": name_s,
                    "type": human,
                    "lang": self._read_lang(src),
                    "selected": "1" if sel_ref else "0",  # наличие kCFBooleanTrue
                })
            return out
        finally:
            CF.CFRelease(arr)

    def switch_by_id(self, source_id: str) -> None:
        arr = self._create_input_source_array()
        if not arr:
            raise RuntimeError("Не удалось получить список источников ввода")
        CF, HT = self._CF, self._HT
        try:
            n = CF.CFArrayGetCount(arr)
            for i in range(n):
                src = self.TISInputSourceRef(CF.CFArrayGetValueAtIndex(arr, i))
                id_ref = HT.TISGetInputSourceProperty(src, self.kTISPropertyInputSourceID) if self.kTISPropertyInputSourceID else None
                if id_ref and self._cfstring_to_py(self.CFStringRef(id_ref)) == source_id:
                    status = HT.TISSelectInputSource(src)
                    if status != 0:
                        raise OSError(status, f"TISSelectInputSource error {status}")
                    return
        finally:
            CF.CFRelease(arr)
        raise ValueError(f"Источник ввода с ID '{source_id}' не найден")

    def switch_by_language(self, lang_code: str) -> None:
        for it in self.list_sources(include_types=("layout","inputmode")):
            if it["lang"] == lang_code:
                self.switch_by_id(it["id"])
                return
        raise RuntimeError(f"Не найден источник для языка '{lang_code}'")

    def find_ids(self, query_substr: str) -> List[str]:
        q = query_substr.lower()
        return [it["id"] for it in self.list_sources(include_types=None)
                if q in it["id"].lower() or q in it["name"].lower()]
