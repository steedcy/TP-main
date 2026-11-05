param([string]$Label = "new", [switch]$SpringOnly)
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "../../..")).Path
$fixture = Join-Path $PSScriptRoot "IndependentF017V161Test.java"
$target = Join-Path $repo "backend/src/test/java/com/airport/ai/task/IndependentF017V161Test.java"
$output = Join-Path $repo ".local-test/f017-v161-independent-$Label.txt"
if ((Test-Path -LiteralPath $target) -or (Test-Path -LiteralPath $output)) { throw "Refusing to overwrite an existing source or observation" }
Copy-Item -LiteralPath $fixture -Destination $target
try {
    $selector = if ($SpringOnly) { "IndependentF017V161Test#productionComponentCanBeCreatedBySpring" } else { "IndependentF017V161Test" }
    & mvn -o -f (Join-Path $repo "backend/pom.xml") test "-Dtest=$selector" *> $output
    $result = $LASTEXITCODE
} finally {
    Remove-Item -LiteralPath $target
}
Write-Output "Maven exit: $result; output: $output"
exit $result
