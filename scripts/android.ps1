param(
  [ValidateSet('user','admin')][string]$App = 'user',
  [string]$JdkHome = 'C:\Program Files\Java\jdk-23',
  [string]$ApiBaseUrl = 'http://localhost:8000'
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$gradle = Join-Path $env:USERPROFILE '.cache\dsbca-gradle\gradle-8.14\bin\gradle.bat'
$previousJava = $env:JAVA_HOME
$env:JAVA_HOME = $JdkHome
Push-Location (Join-Path $projectRoot "apps\dsbca_$App\android")
try {
  $definition = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("API_BASE_URL=$ApiBaseUrl"))
  $compatArgs = @()
  $helperPath = Join-Path $env:USERPROFILE '.cache\dsbca-flutter\packages\flutter_tools\gradle\src\main\kotlin\tasks\BaseFlutterTaskHelper.kt'
  if ((Test-Path $helperPath) -and (Get-Content -LiteralPath $helperPath -Raw).Contains('args("--DartDefines=$it")')) {
    $env:DSBCA_REAL_FLUTTER = Join-Path $env:USERPROFILE '.cache\dsbca-flutter\bin\flutter.bat'
    $env:DSBCA_FLUTTER_WRAPPER = Join-Path $PSScriptRoot 'flutter-assemble-compat.cmd'
    $compatArgs = @('--init-script', (Join-Path $PSScriptRoot 'flutter-assemble-compat.gradle'))
  }
  if (Test-Path $gradle) { & $gradle @compatArgs assembleDebug "-Dorg.gradle.java.home=$JdkHome" "-Pdart-defines=$definition" }
  else { & .\gradlew.bat @compatArgs assembleDebug "-Dorg.gradle.java.home=$JdkHome" "-Pdart-defines=$definition" }
  if ($LASTEXITCODE -ne 0) { throw "Android build failed: $LASTEXITCODE" }
} finally { Pop-Location; $env:JAVA_HOME = $previousJava }
