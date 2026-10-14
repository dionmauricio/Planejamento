# Planejamento de Produção

Aplicação web para substituir a planilha **Curva S Estação de Emenda.xlsx**. O
backend é Python/Flask, os dados operacionais são persistidos no PostgreSQL e a
interface web apresenta as nove abas do arquivo de origem.

## Abas e regras implementadas

| Aba original | Tela do sistema | Dados apresentados |
| --- | --- | --- |
| Curva S | Curva S | Planejamento e apontamentos diários |
| Indicadores Semanais | Indicadores Semanais | Consolidação semanal derivada da curva diária |
| Curva S Preparação | Curva S Preparação | Planejamento e produção semanal da etapa |
| Curva S Montagem | Curva S Montagem | Planejamento e produção semanal da etapa |
| Curva S Soldagem | Curva S Soldagem | Planejamento e produção semanal da etapa |
| Curva S Acabamento | Curva S Acabamento | Planejamento e produção semanal da etapa |
| Curva S Pintura | Curva S Pintura | Planejamento e produção semanal da etapa |
| Base Tarefas | Base Tarefas | Cadastro, pesos planejados, fabricados e expedidos |
| Resumo por Área | Resumo por Área | Resumo carregado da aba original |

O avanço físico é ponderado exclusivamente pelo peso, não pela quantidade de
tarefas. Para cada período, o sistema calcula:

- avanço planejado acumulado = peso planejado acumulado ÷ peso planejado total;
- avanço fabricado acumulado = peso fabricado acumulado ÷ peso planejado total;
- desvio acumulado = peso fabricado acumulado − peso planejado acumulado;
- situação = **No prazo** quando o avanço fabricado acumulado é maior ou igual
  ao planejado; caso contrário, **Atrasado**;
- avanço de uma tarefa = peso fabricado ÷ peso planejado (zero quando o peso
  planejado é zero).

Os pesos devem ser finitos e não negativos, com precisão de até três casas
decimais. A aplicação não limita o peso fabricado ao peso planejado, permitindo
registrar excedentes reais. A aba Indicadores Semanais do arquivo está vazia;
no sistema, ela passa a consolidar as semanas da Curva S diária. O Resumo por
Área é preservado como retrato da aba de origem, pois seu universo de tarefas
(159) não coincide com a Base Tarefas fornecida (107 linhas).
As datas e horários de início e término das tarefas são importados e mantidos.
Também foram mantidas as datas existentes nas linhas de cada curva, sem
substituí-las pelos textos-resumo de período: algumas datas da Curva S semanal
não coincidem com o intervalo descritivo da própria aba. A planilha informa
produção média de 1.300 kg/dia e 60 dias úteis, embora o peso planejado total
seja 74.810 kg; o sistema usa os pesos e datas de cada linha como fonte de
cálculo, sem propagar esses metadados inconsistentes como regras calculadas.

## Executar com Docker Compose

É necessário ter Docker Desktop e Docker Compose instalados.

1. Copie `.env.example` para `.env` e defina uma senha forte para
   `POSTGRES_PASSWORD`.
2. No PowerShell, na pasta do projeto:

   ```powershell
   docker compose up --build -d
   docker compose exec web flask --app app:create_app import-workbook /app/data/source.xlsx
   ```

3. Acesse [http://localhost:8000](http://localhost:8000). A saúde da aplicação
   e a conexão ao PostgreSQL podem ser conferidas em `/health`.

O volume nomeado `postgres_data` mantém os dados quando os containers são
reiniciados. Para reimportar e substituir as tarefas, curvas e resumos já
existentes, execute conscientemente:

```powershell
docker compose exec web flask --app app:create_app import-workbook --replace /app/data/source.xlsx
```

`--replace` apaga os registros operacionais antes da nova importação; faça um
backup do banco antes de utilizá-lo.

## Executar localmente no Windows

Use Python 3.12 e um PostgreSQL acessível. Crie um banco chamado `planejamento`,
configure `DATABASE_URL`, instale as dependências e importe a planilha:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:DATABASE_URL = "postgresql+psycopg://planejamento:SENHA@localhost:5432/planejamento"
flask --app app:create_app import-workbook ".\Curva S Estação de Emenda.xlsx"
waitress-serve --listen=127.0.0.1:8000 --call app:create_app
```

As tabelas são criadas na inicialização da aplicação. A primeira importação não
substitui dados existentes; o comando falha de forma explícita caso o banco já
contenha dados.
Caracteres especiais na senha de `DATABASE_URL` devem ser percent-encoded.

## API

- `GET /api/planilhas`: lista as abas disponíveis.
- `GET /api/planilhas/<chave>`: retorna indicadores e linhas da aba.
- `PUT /api/planilhas/<chave>/periodos/<id>`: atualiza o peso fabricado de um
  período de curva.
- `POST /api/tarefas`, `PATCH /api/tarefas/<id>`, `PUT /api/tarefas/<id>` e
  `DELETE /api/tarefas/<id>`: operações da Base Tarefas.
- `GET /exportar/<chave>.csv`: exporta os dados de uma aba em CSV compatível
  com Excel.
- `GET /health`: confirma a disponibilidade do PostgreSQL.

As chaves das abas são `curva-s`, `indicadores-semanais`,
`curva-s-preparacao`, `curva-s-montagem`, `curva-s-soldagem`,
`curva-s-acabamento`, `curva-s-pintura`, `base-tarefas` e
`resumo-por-area`.

## Testes

```powershell
python -m unittest discover -s tests -v
```

## Implantação

O Compose fornecido é uma configuração inicial para rede controlada. Antes de
publicar o serviço, configure credenciais fortes, TLS e autenticação/autorização
institucional no proxy de entrada; a aplicação não implementa contas de usuário
ou controle de acesso.
