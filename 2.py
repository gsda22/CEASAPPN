import streamlit as st
import sqlite3
import hashlib
import pandas as pd
from PIL import Image
import datetime
import pytz
from babel.dates import format_datetime

# [Outras funções permanecem as mesmas até a seção Streamlit app...]

# Streamlit app
st.set_page_config(page_title="Gerenciamento CEASA", page_icon="🍎", layout="wide")

# Logo
logo = Image.open("logo.png")  # Assume logo.png na mesma pasta
st.image(logo, width=200)

# Calculadora na barra lateral
with st.sidebar:
    st.subheader("Calculadora Rápida")
    calc_input = st.text_input("Digite o cálculo (ex.: 25+25)", key="calculadora")
    if calc_input:
        try:
            result = eval(calc_input)  # Avaliação simples, cuidado com entradas
            st.write(f"Resultado: {result}")
        except:
            st.error("Cálculo inválido")

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None
    st.session_state.user_id = None
    st.session_state.username = None

if not st.session_state.logged_in:
    st.title("Login")
    with st.form(key="login_form"):
        username = st.text_input("Usuário", placeholder="Digite seu usuário", help="Usuário padrão: admin")
        password = st.text_input("Senha", type="password", placeholder="Digite sua senha", help="Senha padrão: 123456")
        submit = st.form_submit_button("Entrar")
    
    if submit:
        role = check_credentials(username, password)
        if role:
            st.session_state.logged_in = True
            st.session_state.role = role
            st.session_state.username = username
            st.session_state.user_id = get_user_id(username)
            st.success("Login realizado com sucesso!")
            st.rerun()  # Correção: Substitui st.experimental_rerun()
        else:
            st.error("Usuário ou senha inválidos")
else:
    st.sidebar.title(f"Bem-vindo, {st.session_state.username} ({st.session_state.role})")
    if st.sidebar.button("Sair"):
        st.session_state.logged_in = False
        st.session_state.role = None
        st.session_state.user_id = None
        st.session_state.username = None
        st.rerun()  # Correção: Substitui st.experimental_rerun()
    
    if st.session_state.role == "admin":
        change_pass = st.sidebar.checkbox("Alterar Senha")
        if change_pass:
            with st.sidebar.form("change_pass_form"):
                new_pass = st.text_input("Nova Senha", type="password")
                confirm_pass = st.text_input("Confirmar Senha", type="password")
                submit_change = st.form_submit_button("Alterar")
                if submit_change and new_pass == confirm_pass:
                    change_password(st.session_state.user_id, new_pass)
                    st.sidebar.success("Senha alterada com sucesso!")
                elif submit_change:
                    st.sidebar.error("As senhas não coincidem")
    
    tab1, tab2, tab3, tab4 = st.tabs(["Registrar às Cegas", "Auditar", "Relatórios", "Gerenciar Usuários"])
    
    with tab1:
        if st.session_state.role in ["admin", "registrar"]:
            st.header("Registrar CEASA às Cegas")
            
            # Upload de arquivo Excel
            uploaded_file = st.file_uploader("Carregar arquivo Excel com produtos (colunas: codigo, descricao, secao)", type="xlsx", key="excel_uploader")
            if uploaded_file is not None:
                with st.spinner("Processando o upload do Excel..."):
                    if upload_products(uploaded_file):
                        st.rerun()  # Correção: Substitui st.experimental_rerun()
                    else:
                        st.stop()  # Para a execução se houver erro
            
            # Exibir tabela de produtos para depuração
            st.subheader("Produtos Cadastrados")
            products_df = get_all_products_df()
            if products_df.empty:
                st.info("Nenhum produto cadastrado no banco de dados.")
            else:
                st.dataframe(products_df)
            
            # Input de código do produto
            product_code = st.text_input("Código do Produto", placeholder="Digite o código do produto (ex.: 001)", key="product_code_input")
            product_id = None
            if product_code:
                if product_code.strip() == "":
                    st.error("O código do produto não pode estar vazio.")
                else:
                    product = get_product_by_code(product_code)
                    if product:
                        product_id, code, name, category, unit = product
                        st.write(f"**Descrição**: {name}")
                        st.write(f"**Seção**: {category}")
                        st.write(f"**Unidade**: {unit}")
                    else:
                        st.warning(f"Produto com código '{product_code}' não encontrado.")
                        add_new = st.checkbox("Adicionar este produto ao banco de dados?", key="add_new_product")
                        if add_new:
                            with st.form("add_new_product_form"):
                                new_code = st.text_input("Código", value=product_code, disabled=True)
                                new_name = st.text_input("Descrição")
                                new_category = st.text_input("Seção")
                                new_unit = st.text_input("Unidade (ex.: kg)")
                                if st.form_submit_button("Adicionar Produto"):
                                    if new_name.strip() == "" or new_code.strip() == "":
                                        st.error("O código e a descrição do produto não podem estar vazios.")
                                    else:
                                        add_product(new_code, new_name, new_category, new_unit)
                                        st.rerun()  # Correção: Substitui st.experimental_rerun()
            
            stores = get_stores()
            store_options = {name: id for id, name in stores}
            selected_store = st.selectbox("Loja", list(store_options.keys()), key="store_select")
            quantity = st.number_input("Quantidade", min_value=0.0, key="quantity_input")
            if st.button("Registrar", key="register_button"):
                if product_id:
                    register_blind(product_id, store_options[selected_store], quantity, st.session_state.user_id)
                    st.success("Registrado com sucesso!")
                else:
                    st.error("Selecione um produto válido antes de registrar.")
        else:
            st.error("Acesso negado.")
    
    with tab2:
        if st.session_state.role in ["admin", "auditor"]:
            st.header("Auditar Quantidade Recebida")
            regs = get_registrations_without_audit()
            if regs.empty:
                st.info("Nenhum registro para auditar.")
            else:
                st.dataframe(regs)
                reg_id = st.number_input("ID do Registro para Auditar", min_value=1, key="audit_reg_id")
                actual_qty = st.number_input("Quantidade Real", min_value=0.0, key="audit_qty")
                if st.button("Auditar", key="audit_button"):
                    audit_registration(reg_id, actual_qty, st.session_state.user_id)
                    st.success("Auditado com sucesso!")
                    st.rerun()  # Correção: Substitui st.experimental_rerun()
        else:
            st.error("Acesso negado.")
    
    with tab3:
        st.header("Relatórios: Produtos com Maior Divergência")
        # Filtros
        categories = get_unique_categories()
        selected_category = st.selectbox("Filtrar por Seção", categories, key="category_filter")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            start_date = st.date_input("Data Inicial", value=datetime.datetime.now(BRASILIA_TZ).date(), key="start_date")
        with col2:
            end_date = st.date_input("Data Final", value=datetime.datetime.now(BRASILIA_TZ).date(), key="end_date")
        with col3:
            users = get_unique_users()
            selected_user = st.selectbox("Filtrar por Usuário", users, key="user_filter")
        
        # Converter datas para formato do banco (UTC)
        start_date_str = start_date.strftime('%Y-%m-%d 00:00:00')
        end_date_str = end_date.strftime('%Y-%m-%d 23:59:59')
        
        # Obter relatório com filtros
        div = get_divergent_products(
            category_filter=selected_category if selected_category != "Todas" else None,
            start_date=start_date_str if start_date else None,
            end_date=end_date_str if end_date else None,
            user_filter=selected_user if selected_user != "Todos" else None
        )
        if div.empty:
            st.info("Nenhum dado disponível para os filtros selecionados.")
        else:
            st.dataframe(div)
    
    with tab4:
        if st.session_state.role == "admin":
            st.header("Gerenciar Usuários")
            users_df = get_users()
            st.dataframe(users_df)
            
            st.subheader("Adicionar Usuário")
            with st.form("add_user"):
                new_username = st.text_input("Usuário")
                new_password = st.text_input("Senha", type="password")
                new_role = st.selectbox("Papel", ["registrador", "auditor", "admin"])
                if st.form_submit_button("Adicionar"):
                    add_user(new_username, new_password, new_role)
                    st.success("Usuário adicionado!")
                    st.rerun()  # Correção: Substitui st.experimental_rerun()
            
            st.subheader("Excluir Usuário")
            del_user_id = st.number_input("ID do Usuário para Excluir", min_value=1)
            if st.button("Excluir", key="delete_user_button"):
                delete_user(del_user_id)
                st.success("Usuário excluído!")
                st.rerun()  # Correção: Substitui st.experimental_rerun()
        else:
            st.error("Acesso negado.")

# [O restante das funções (get_divergent_products, etc.) permanece o mesmo]
