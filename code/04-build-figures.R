#!/usr/bin/env Rscript
# Thin batch wrapper; the stepwise routes contain the complete plotting workflow.
arg <- grep("^--file=", commandArgs(FALSE), value = TRUE)
code_dir <- if (length(arg)) dirname(normalizePath(gsub("~+~", " ", sub("^--file=", "", arg[[1]]), fixed = TRUE))) else file.path(getwd(), "code")
for (name in c("02-main-figures-stepwise.R", "03-si-figures-stepwise.R")) {
  source(file.path(code_dir, name), local = new.env(parent = globalenv()))
}
