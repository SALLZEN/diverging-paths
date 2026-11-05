#include <Rinternals.h>
#include <CoreFoundation/CoreFoundation.h>
#include <CoreText/CoreText.h>
SEXP damadi_register_fonts(SEXP paths) {
  for (R_xlen_t i=0;i<XLENGTH(paths);i++) {
    CFStringRef path=CFStringCreateWithCString(NULL,CHAR(STRING_ELT(paths,i)),kCFStringEncodingUTF8);
    CFURLRef url=CFURLCreateWithFileSystemPath(NULL,path,kCFURLPOSIXPathStyle,false);
    CFErrorRef font_error=NULL;
    Boolean ok=CTFontManagerRegisterFontsForURL(url,kCTFontManagerScopeProcess,&font_error);
    CFIndex code=font_error ? CFErrorGetCode(font_error) : 0;
    CFRelease(url);CFRelease(path);
    if(font_error) CFRelease(font_error);
    if(!ok && code!=kCTFontManagerErrorAlreadyRegistered) Rf_error("Could not register bundled STIX font (CoreText error %ld)",(long)code);
  }
  return ScalarLogical(1);
}
