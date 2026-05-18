# 🌊 Gerenciador de Piscinas

Um aplicativo web interativo desenvolvido com [Streamlit](https://streamlit.io/) para auxiliar no gerenciamento e monitoramento da qualidade da água de piscinas. Ele permite que os usuários registrem medições de vários parâmetros químicos, acompanhem o histórico através de gráficos e recebam recomendações automáticas para manter a água saudável.

## 🚀 Funcionalidades

*   **🔐 Sistema de Contas:** Cadastro e login de usuários seguros (senhas hasheadas).
*   **🏊‍♂️ Múltiplas Piscinas:** Um usuário pode gerenciar várias piscinas, configurando nomes e volumes (m³).
*   **📝 Registro de Parâmetros:** Permite registrar medições de:
    *   pH
    *   Cloro (ppm)
    *   Nível do Gerador de Cloro (%)
    *   Alcalinidade (em gotas - convertida para ppm)
    *   Dureza Cálcica (em gotas - convertida para ppm)
    *   Salinidade (em gotas - convertida para ppm e g/L)
*   **📊 Histórico e Gráficos:** Visualização em tabela de todo o histórico da piscina com gráficos interativos (via Plotly) de tendência ao longo do tempo.
*   **💡 Diagnóstico e Recomendações:** O app analisa as últimas medições e fornece status visual (✅ Dentro, 🟡 Limite, 🔻 Abaixo, 🔺 Acima) e recomendações práticas (ex: dosagem de bicarbonato calculada pelo volume da piscina).
*   **⚙️ Gerenciamento de Dados:** Edição e exclusão de registros de medições passadas.

## 🛠️ Tecnologias Utilizadas

*   [Python 3](https://www.python.org/)
*   [Streamlit](https://streamlit.io/) - Framework web
*   [Pandas](https://pandas.pydata.org/) - Manipulação e análise de dados
*   [Plotly](https://plotly.com/python/) - Criação de gráficos interativos
*   **SQLite3** - Banco de dados local (`piscina_data.db`)

## ⚙️ Instalação e Execução

### Pré-requisitos
Certifique-se de ter o Python instalado na sua máquina. 

### Passo a passo

1.  **Clone o repositório:**
    ```bash
    git clone https://github.com/SEU_USUARIO/NOME_DO_REPOSITORIO.git
    cd NOME_DO_REPOSITORIO
    ```

2.  **Crie e ative um ambiente virtual (recomendado):**
    ```bash
    python -m venv venv
    # No Windows:
    venv\Scripts\activate
    # No Linux/Mac:
    source venv/bin/activate
    ```

3.  **Instale as dependências:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Execute o aplicativo:**
    ```bash
    streamlit run app.py
    ```

5.  Acesse no seu navegador através do endereço local fornecido (geralmente `http://localhost:8501`).

## 📁 Estrutura do Projeto

*   `app.py`: Arquivo principal da interface de usuário em Streamlit e lógicas de front-end.
*   `database.py`: Funções para interação com o banco de dados SQLite (CRUD, Autenticação).
*   `pool_tips.json`: Arquivo de configuração contendo os textos e recomendações para o status da piscina.
*   `requirements.txt`: Lista de dependências do Python necessárias para rodar o projeto.
*   `piscina_data.db`: Banco de dados gerado automaticamente na primeira execução.

## 🤝 Contribuição
Sinta-se à vontade para abrir *Issues* relatando bugs ou *Pull Requests* sugerindo melhorias!

## 📄 Licença
Este projeto é de código aberto. Sinta-se livre para utilizá-lo e modificá-lo.
