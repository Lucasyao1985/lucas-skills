param(
    [Parameter(Mandatory = $true)][string]$Url,
    [Parameter(Mandatory = $true)][string]$OutFile,
    [Parameter(Mandatory = $false)][string]$LogFile,
    [Parameter(Mandatory = $false)][string]$ExtraHeaders = ""
)

# Fetch a URL on Windows where curl inside a bash sandbox has no outbound
# network. Writes the body to $OutFile (UTF-8) and a STATUS line to $LogFile.
# $ExtraHeaders is a JSON object string merged into the default headers.
# Exit code 0 = success, 1 = failure.

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$headers = @{
    'User-Agent'      = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    'Accept'          = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    'Accept-Language' = 'en-US,en;q=0.9'
}

if ($ExtraHeaders -and $ExtraHeaders.Trim().Length -gt 0) {
    try {
        $extra = $ExtraHeaders | ConvertFrom-Json
        foreach ($p in $extra.PSObject.Properties) {
            $headers[$p.Name] = [string]$p.Value
        }
    }
    catch {
        Write-Output "WARN=could not parse ExtraHeaders: $($_.Exception.Message)"
    }
}

try {
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
    $resp = Invoke-WebRequest -Uri $Url -Headers $headers -UseBasicParsing -TimeoutSec 90 -MaximumRedirection 5

    $dir = Split-Path -Parent $OutFile
    if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

    [System.IO.File]::WriteAllText($OutFile, $resp.Content, (New-Object System.Text.UTF8Encoding($false)))

    $msg = "STATUS=$($resp.StatusCode) LEN=$($resp.Content.Length) URL=$Url"
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
