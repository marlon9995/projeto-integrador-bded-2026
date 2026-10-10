param([switch]$Stop)
$ErrorActionPreference = 'Stop'
$base = $PSScriptRoot
$runtime = Join-Path $base 'runtime'
$data = Join-Path $runtime 'pgdata'
$pg = Join-Path $base '.tools/pgsql/bin'
$shared = Join-Path (Split-Path $base -Parent) '.tools/pgsql/bin'
if (!(Test-Path (Join-Path $pg 'pg_ctl.exe')) -and (Test-Path (Join-Path $shared 'pg_ctl.exe'))) { $pg=$shared }
if (!(Test-Path (Join-Path $pg 'pg_ctl.exe'))) {
    $tools=Join-Path $base '.tools'
    New-Item -ItemType Directory -Force $tools | Out-Null
    Invoke-WebRequest 'https://get.enterprisedb.com/postgresql/postgresql-17.11-3-windows-x64-binaries.zip' -OutFile (Join-Path $tools 'postgresql.zip')
    Expand-Archive -LiteralPath (Join-Path $tools 'postgresql.zip') -DestinationPath $tools -Force
}
if ($Stop) {
    & (Join-Path $pg 'pg_ctl.exe') -D $data -m fast -w stop
    exit $LASTEXITCODE
}
New-Item -ItemType Directory -Force $runtime | Out-Null
if (!(Test-Path (Join-Path $data 'PG_VERSION'))) {
    & (Join-Path $pg 'initdb.exe') -D $data -U integrador -A trust --encoding=UTF8 --locale=C
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao inicializar banco' }
    # Nenhum servidor foi iniciado com trust. A autenticacao usa a conta Windows atual.
    Set-Content -LiteralPath (Join-Path $data 'pg_hba.conf') -Encoding ascii -Value 'host all integrador 127.0.0.1/32 sspi include_realm=0 map=usuario_local'
    $accountPattern=[regex]::Escape($env:USERNAME)
    $mapping='usuario_local "/(?i)^' + $accountPattern + '$" integrador'
    Set-Content -LiteralPath (Join-Path $data 'pg_ident.conf') -Encoding ascii -Value $mapping
}
& (Join-Path $pg 'pg_ctl.exe') -D $data status
if ($LASTEXITCODE -ne 0) {
    & (Join-Path $pg 'pg_ctl.exe') -D $data -l (Join-Path $runtime 'postgres.log') -o '-h 127.0.0.1 -p 55433' -w start
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao iniciar banco; veja runtime/postgres.log' }
}
$exists=& (Join-Path $pg 'psql.exe') -h 127.0.0.1 -p 55433 -U integrador -d postgres -Atc "SELECT 1 FROM pg_database WHERE datname='mobilidade'"
if ($LASTEXITCODE -ne 0) { throw 'Falha de autenticacao integrada' }
if ($exists -ne '1') {
    & (Join-Path $pg 'createdb.exe') -h 127.0.0.1 -p 55433 -U integrador mobilidade
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar banco' }
}
Write-Output 'Banco persistente pronto: mobilidade / 127.0.0.1:55433. Autenticacao Windows.'
