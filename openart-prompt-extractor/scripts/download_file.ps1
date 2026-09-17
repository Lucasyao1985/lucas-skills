param(
    [Parameter(Mandatory = $true)][string]$Url,
    [Parameter(Mandatory = $true)][string]$OutFile,
    [Parameter(Mandatory = $false)][string]$LogFile
)

# Binary-safe download (mp4/webp/...). Uses Invoke-WebRequest -OutFile so bytes
# are written verbatim. Writes a STATUS line (code / bytes) to $LogFile.
# Exit code 0 = success, 1 = failure.

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$headers = @{
    'User-Agent' = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    'Referer'    = 'https://openart.ai/'
}

try {
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
    $dir = Split-Path -Parent $OutFile
    if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

    Invoke-WebRequest -Uri $Url -Headers $headers -OutFile $OutFile -TimeoutSec 300 -MaximumRedirection 5

    $size = (Get-Item $OutFile).Length
    $msg = "STATUS=200 BYTES=$size FILE=$OutFile"
    if ($LogFile) {
        [System.IO.File]::WriteAllText($LogFile, $msg, (New-Object System.Text.UTF8Encoding($false)))
    }
    Write-Output $msg
    exit 0
}
catch {
    $msg = "ERROR=$($_.Exception.Message) URL=$Url"
    if ($LogFile) {
        [System.IO.File]::WriteAllText($LogFile, $msg, (New-Object System.Text.UTF8Encoding($false)))
    }
    Write-Output $msg
    exit 1
}
