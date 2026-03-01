# campfire-gooners
Digging In Paris – a small pygame mining game.

## Packaging for itch.io with `pygbag`

This project is structured so it can be built into a web executable via
[pygbag](https://github.com/pygame-web/pygbag).  The helper script
`package.ps1` and `requirements.txt` are provided to simplify the process.

### Quick start

1. Create/activate a Python environment.
2. Install dependencies:
   ```sh
   pip install -r requirements.txt pygbag
   ```
3. Run the packager (PowerShell):
   ```powershell
   .\package.ps1
   ```

The helper invokes `pygbag` with the current CLI, which for the installed
version will build into `build/web` by default and use `requirements.txt`
for dependencies.  Adjust the command‑line flags in `package.ps1` if you
need to specify a different icon, title, or tweak other options.

## Development

Run the game locally with:

```sh
python main.py
```

and edit the source files as desired.
