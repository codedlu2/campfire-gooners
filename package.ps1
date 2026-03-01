<#
PowerShell helper to package the game using pygbag (pyodide/wasm build).
Usage:
    Install pygbag if you haven't already:
        pip install pygbag

    Then run this script from the repo root:
        .\package.ps1

By default it will build into a `dist/` folder and include all .py files
and the assets directory; adjust the command-line flags below as needed.
#>

# make sure we're in the repo root
Push-Location -Path $PSScriptRoot

pygbag --build . `
    --package requirements.txt `
    --title "Digging In Paris" `
    --icon assets/images/dip_playerv2.png `
    --clean
    # note: this version of pygbag always writes into build\web; if you want
    # a different output location move/rename that directory after building.

Pop-Location