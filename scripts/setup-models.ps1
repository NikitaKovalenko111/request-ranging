[CmdletBinding()]
param(
    [ValidateSet("3.11", "3.12", "3.13")]
    [string]$PythonVersion = "3.12",

    [ValidateRange(3, 1000000)]
    [int]$RankerOrders = 5000,

    [ValidateRange(1, 100000)]
    [int]$RankerIterations = 350,

    [switch]$Force,
    [switch]$SkipDependencyInstall,
    [switch]$SkipVerification,
    [switch]$BuildDecisionEngineImage
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$projectRoot = Join-Path $repoRoot "decision-engine"
$venvRoot = Join-Path $projectRoot ".venv"
$pythonExe = Join-Path $venvRoot "Scripts\python.exe"

$embeddingRoot = Join-Path $projectRoot "models\feature-extractor\matching\paraphrase-multilingual-MiniLM-L12-v2"
$classifierRoot = Join-Path $projectRoot "models\feature-extractor\classifier\best"
$rankerModel = Join-Path $projectRoot "models\ranker-v2.cbm"
$rankerMetadata = Join-Path $projectRoot "models\ranker-v2.metadata.json"

$embeddingFiles = @(
    "config.json",
    "config_sentence_transformers.json",
    "model.safetensors",
    "modules.json",
    "sentence_bert_config.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "1_Pooling\config.json"
)
$classifierFiles = @(
    "config.json",
    "labels.json",
    "model.pt",
    "tokenizer.json",
    "tokenizer_config.json"
)

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Invoke-External {
    param(
        [Parameter(Mandatory)]
        [string]$FilePath,

        [Parameter(Mandatory)]
        [string[]]$Arguments,

        [Parameter(Mandatory)]
        [string]$Description
    )

    Write-Step $Description
    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE."
    }
}

function Test-ModelFiles {
    param(
        [Parameter(Mandatory)]
        [string]$Root,

        [Parameter(Mandatory)]
        [string[]]$RequiredFiles
    )

    if (-not (Test-Path -LiteralPath $Root -PathType Container)) {
        return $false
    }

    foreach ($relativePath in $RequiredFiles) {
        $candidate = Join-Path $Root $relativePath
        if (-not (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            return $false
        }
        if ((Get-Item -LiteralPath $candidate).Length -eq 0) {
            return $false
        }
    }
    return $true
}

function Assert-File {
    param(
        [Parameter(Mandatory)]
        [string]$Path,

        [Parameter(Mandatory)]
        [string]$Description
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "$Description was not created: $Path"
    }
    if ((Get-Item -LiteralPath $Path).Length -eq 0) {
        throw "$Description is empty: $Path"
    }
}

if (-not (Test-Path -LiteralPath $projectRoot -PathType Container)) {
    throw "Decision Engine directory was not found: $projectRoot"
}

if (-not (Test-Path -LiteralPath $pythonExe -PathType Leaf)) {
    Write-Step "Creating Python $PythonVersion virtual environment"
    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($null -ne $pyLauncher) {
        $externalArgs = @{
            FilePath = $pyLauncher.Source
            Arguments = @("-$PythonVersion", "-m", "venv", $venvRoot)
            Description = "Create virtual environment"
        }
        Invoke-External @externalArgs
    }
    else {
        $systemPython = Get-Command python -ErrorAction SilentlyContinue
        if ($null -eq $systemPython) {
            throw "Python was not found. Install Python 3.11+ or the Windows py launcher."
        }
        $externalArgs = @{
            FilePath = $systemPython.Source
            Arguments = @("-m", "venv", $venvRoot)
            Description = "Create virtual environment"
        }
        Invoke-External @externalArgs
    }
}

$externalArgs = @{
    FilePath = $pythonExe
    Arguments = @(
        "-c",
        "import sys; assert sys.version_info >= (3, 11), 'Python 3.11+ is required'; print(sys.version)"
    )
    Description = "Check Python version"
}
Invoke-External @externalArgs

if (-not $SkipDependencyInstall) {
    $externalArgs = @{
        FilePath = $pythonExe
        Arguments = @("-m", "pip", "install", "--upgrade", "pip")
        Description = "Upgrade pip"
    }
    Invoke-External @externalArgs

    $externalArgs = @{
        FilePath = $pythonExe
        Arguments = @(
            "-m", "pip", "install",
            "--index-url", "https://download.pytorch.org/whl/cpu",
            "torch"
        )
        Description = "Install CPU PyTorch"
    }
    Invoke-External @externalArgs

    $editableInstall = $projectRoot + "[dev,feature-extractor]"
    $externalArgs = @{
        FilePath = $pythonExe
        Arguments = @("-m", "pip", "install", "-e", $editableInstall)
        Description = "Install Decision Engine dependencies"
    }
    Invoke-External @externalArgs
}
else {
    Write-Host "Dependency installation skipped." -ForegroundColor Yellow
}

$embeddingReady = Test-ModelFiles -Root $embeddingRoot -RequiredFiles $embeddingFiles
if ($Force -or -not $embeddingReady) {
    Push-Location $projectRoot
    try {
        $externalArgs = @{
            FilePath = $pythonExe
            Arguments = @(
                "-m",
                "decision_engine.feature_extractor.matching.download_model"
            )
            Description = "Download sentence-transformer embedding model"
        }
        Invoke-External @externalArgs
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Host "Embedding model already exists; skipping download." -ForegroundColor Green
}

if (-not (Test-ModelFiles -Root $embeddingRoot -RequiredFiles $embeddingFiles)) {
    throw "Embedding model is incomplete after download: $embeddingRoot"
}

$classifierReady = Test-ModelFiles -Root $classifierRoot -RequiredFiles $classifierFiles
if ($Force -or -not $classifierReady) {
    foreach ($datasetName in @("train.csv", "val.csv")) {
        $datasetPath = Join-Path $projectRoot "data\feature_extractor\classifier\$datasetName"
        Assert-File -Path $datasetPath -Description "Classifier dataset"
    }

    Write-Host "Classifier training may take a long time on CPU." -ForegroundColor Yellow
    Push-Location $projectRoot
    try {
        $externalArgs = @{
            FilePath = $pythonExe
            Arguments = @(
                "-m",
                "decision_engine.feature_extractor.classifier.train"
            )
            Description = "Train feature classifier"
        }
        Invoke-External @externalArgs
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Host "Classifier model already exists; skipping training." -ForegroundColor Green
}

if (-not (Test-ModelFiles -Root $classifierRoot -RequiredFiles $classifierFiles)) {
    throw "Classifier model is incomplete after training: $classifierRoot"
}

$rankerReady = (
    (Test-Path -LiteralPath $rankerModel -PathType Leaf) -and
    (Test-Path -LiteralPath $rankerMetadata -PathType Leaf) -and
    ((Get-Item -LiteralPath $rankerModel).Length -gt 0) -and
    ((Get-Item -LiteralPath $rankerMetadata).Length -gt 0)
)
if ($Force -or -not $rankerReady) {
    Push-Location $projectRoot
    try {
        $externalArgs = @{
            FilePath = $pythonExe
            Arguments = @(
                "-m",
                "decision_engine.ml_ranker.train",
                "--orders", [string]$RankerOrders,
                "--iterations", [string]$RankerIterations,
                "--model", $rankerModel,
                "--metadata", $rankerMetadata
            )
            Description = "Train CatBoost ranker v2"
        }
        Invoke-External @externalArgs
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Host "Ranker v2 already exists; skipping training." -ForegroundColor Green
}

Assert-File -Path $rankerModel -Description "Ranker model"
Assert-File -Path $rankerMetadata -Description "Ranker metadata"

if (-not $SkipVerification) {
    $verificationCode = @"
from pathlib import Path
from sentence_transformers import SentenceTransformer
from decision_engine.feature_extractor.classifier.predict import RequestPredictor
from decision_engine.ml_ranker.inference import MLRanker

embedding = Path(r'''$embeddingRoot''')
classifier = Path(r'''$classifierRoot''')
ranker_model = Path(r'''$rankerModel''')
ranker_metadata = Path(r'''$rankerMetadata''')

SentenceTransformer(str(embedding), local_files_only=True, device='cpu')
RequestPredictor(model_dir=classifier, device='cpu')
MLRanker(ranker_model, ranker_metadata)
print('All runtime models loaded successfully.')
"@

    Push-Location $projectRoot
    try {
        $externalArgs = @{
            FilePath = $pythonExe
            Arguments = @("-c", $verificationCode)
            Description = "Verify all runtime models"
        }
        Invoke-External @externalArgs
    }
    finally {
        Pop-Location
    }
}
else {
    Write-Host "Model loading verification skipped." -ForegroundColor Yellow
}

if ($BuildDecisionEngineImage) {
    Push-Location $repoRoot
    try {
        $externalArgs = @{
            FilePath = "docker"
            Arguments = @("compose", "build", "decision-engine")
            Description = "Build Decision Engine Docker image"
        }
        Invoke-External @externalArgs
    }
    finally {
        Pop-Location
    }
}

Write-Host ""
Write-Host "All required Decision Engine models are ready:" -ForegroundColor Green
Write-Host "  Embedding:  $embeddingRoot"
Write-Host "  Classifier: $classifierRoot"
Write-Host "  Ranker:     $rankerModel"
