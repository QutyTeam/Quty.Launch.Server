# ============================================================
# sign-catalog.ps1 — подпись каталога магазина и манифеста обновлений
# ============================================================
# Назначение:
#   Создаёт рядом с JSON файл <имя>.sig (base64) с подписью RSA-3072 + SHA-256.
#   Приложение проверяет её закреплённым публичным ключом
#   (CoreConfig.CATALOG_SIGNING_PUBLIC_KEY, политика REQUIRE).
#
# Когда нужно:
#   - CI подписывает store/shells.json сам (секрет CATALOG_SIGNING_KEY);
#   - этот скрипт — для ручных правок, когда каталог собирается локально
#     или когда нужно переподписать файлы после ручного изменения.
#
# Приватный ключ НЕ хранится в репозитории: держите его вне git
# (по умолчанию D:\Android\Quty.Keys\catalog-signing-key.pem) и в резервной копии.
# Потеря ключа = невозможность выпускать обновления для текущих версий
# приложения: понадобится новая версия ядра с новым закреплённым ключом.
# ============================================================

param(
    [string[]]$Files,
    [string]$KeyPath = "D:\Android\Quty.Keys\catalog-signing-key.pem",
    [string]$OpenSslPath = "C:\Program Files\Git\usr\bin\openssl.exe"
)

$ErrorActionPreference = "Stop"

# По умолчанию подписываем файлы этого репозитория — независимо от текущего каталога.
if (-not $Files -or $Files.Count -eq 0) {
    $Files = @(
        (Join-Path $PSScriptRoot "store\shells.json"),
        (Join-Path $PSScriptRoot "updates\version.json")
    )
}

if (-not (Test-Path $OpenSslPath)) {
    Write-Host "❌ openssl не найден: $OpenSslPath" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $KeyPath)) {
    Write-Host "❌ Ключ подписи не найден: $KeyPath" -ForegroundColor Red
    exit 1
}

$utf8NoBom = New-Object System.Text.UTF8Encoding $false
$failed = 0

foreach ($file in $Files) {
    if (-not (Test-Path $file)) {
        Write-Host "⚠️  пропущен (нет файла): $file" -ForegroundColor Yellow
        continue
    }

    $binPath = Join-Path $env:TEMP ("sig_" + [guid]::NewGuid().ToString("N") + ".bin")

    try {
        & $OpenSslPath dgst -sha256 -sign $KeyPath -out $binPath $file

        if ($LASTEXITCODE -ne 0 -or -not (Test-Path $binPath)) {
            throw "openssl завершился с кодом $LASTEXITCODE"
        }

        $base64 = [Convert]::ToBase64String([System.IO.File]::ReadAllBytes($binPath))
        [System.IO.File]::WriteAllText("$file.sig", $base64, $utf8NoBom)

        Write-Host "✅ $file.sig ($($base64.Length) символов base64)" -ForegroundColor Green
    } catch {
        Write-Host "❌ $file : $($_.Exception.Message)" -ForegroundColor Red
        $failed++
    } finally {
        if (Test-Path $binPath) { Remove-Item $binPath -Force }
    }
}

if ($failed -gt 0) {
    Write-Host ""
    Write-Host "Не удалось подписать файлов: $failed" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Готово. Не забудьте закоммитить .sig вместе с JSON." -ForegroundColor Cyan
exit 0
