# Manual copy manifest for GitHub

Use these files to copy the complete project without truncating `app.py`.

Target structure:

```text
Proyecto-Sin-Pausas/
├── README.md
├── .gitignore
└── proyectos/
    └── sabrina_ai_lab/
        ├── README.md
        └── app.py
```

Copy order:

1. `COPY_01_ROOT_README.md`
2. `COPY_02_GITIGNORE.md`
3. `COPY_03_SABRINA_AI_LAB_README.md`
4. `COPY_04_APP_PY_PART_01_OF_05.md`
5. `COPY_04_APP_PY_PART_02_OF_05.md`
6. `COPY_04_APP_PY_PART_03_OF_05.md`
7. `COPY_04_APP_PY_PART_04_OF_05.md`
8. `COPY_04_APP_PY_PART_05_OF_05.md`

For `app.py`, concatenate all `COPY_04_APP_PY_PART_*` chunks in numeric order, without the Markdown fences.
