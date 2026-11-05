# Load bundled static faces only in this R process; never install system fonts.
register_damadi_quartz_fonts <- function(font_dir, runtime_dir, source_file) {
  dir.create(runtime_dir, recursive = TRUE, showWarnings = FALSE)
  library_file <- file.path(runtime_dir, paste0("damadi-quartz-fonts", .Platform$dynlib.ext))
  if (!file.exists(library_file) || file.mtime(library_file) < file.mtime(source_file)) {
    file.copy(source_file, file.path(runtime_dir, "register-quartz-fonts.c"), overwrite = TRUE)
    previous_dir <- getwd(); previous_libs <- Sys.getenv("PKG_LIBS", unset = NA_character_)
    on.exit(setwd(previous_dir), add = TRUE)
    on.exit(if (is.na(previous_libs)) Sys.unsetenv("PKG_LIBS") else Sys.setenv(PKG_LIBS = previous_libs), add = TRUE)
    setwd(runtime_dir)
    Sys.setenv(PKG_LIBS = "-framework CoreText -framework CoreFoundation")
    status <- system2(file.path(R.home("bin"), "R"), c("CMD", "SHLIB", "register-quartz-fonts.c", "-o", basename(library_file)), stdout = "build.log", stderr = "build.log")
    if (status != 0L || !file.exists(library_file)) stop("Could not prepare the process-local Quartz font helper. Check .runtime/quartz-fonts/build.log; macOS command-line compiler tools are required.")
    setwd(previous_dir)
  }
  dyn.load(library_file)
  faces <- c("STIXTwoText-Regular.ttf", "STIXTwoText-Medium.ttf", "STIXTwoText-Italic.ttf", "STIXTwoText-MediumItalic.ttf")
  stopifnot(isTRUE(.Call("damadi_register_fonts", file.path(font_dir, faces))))
  quartzFonts("STIX Two Text" = c("STIXTwoText-Regular", "STIXTwoText-Medium", "STIXTwoText-Italic", "STIXTwoText-MediumItalic"))
}
