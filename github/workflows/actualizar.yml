name: Actualizar tasa BCV

on:
  schedule:
    - cron: "*/10 * * * *"
  workflow_dispatch:

permissions:
  contents: write

concurrency:
  group: tasa-bcv
  cancel-in-progress: false

jobs:
  actualizar:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install requests
      - run: python actualizar.py
      - name: Guardar cambios
        run: |
          git config user.name "tasa-bot"
          git config user.email "tasa-bot@users.noreply.github.com"
          git add tasa.json
          git diff --staged --quiet || (git commit -m "Actualizar tasa BCV" && git push)
