# Diverging Paths package map

    diverging-paths/
      README.md
      run.sh
      setup-environment.sh
      code/                     shared workflow, stepwise renderers and retained upstream sources
      notebooks/                clean shared-function notebook
      data/                     exact inputs, transport parts and retained statistical products
      network/                  unchanged frozen network ZIPs and earlier source/summaries
      figures/                  earlier figure assets
        normalized/             approved normalized manuscript PDF references
      resources/                bundled fonts and retained network artwork
      provenance/v3.0.0/        unchanged predecessor metadata and manifest
      checks/                   retained input pins
      config/                   current workspace and figure profiles
      reproduced/               generated products, ignored
      verification/             generated checks, ignored
      executed-notebooks/       private-kernel output, ignored
      .runtime/                 disposable environment/caches, ignored

The normalized route is inputs -> integrity checks -> corpus/candidate reconstruction -> 57 frozen network checks -> optional approved figure renderings -> run report.

The original upstream pipeline remains available for historical research maintenance, with a separate scope and environment. It is not the default route and does not claim exact raw-text recreation of archived network events.
