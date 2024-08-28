import streamlit as st
import pandas as pd
import sqlite3
import openpyxl

# Connexion à la base de données SQLite
conn = sqlite3.connect('inventory_management.db')
c = conn.cursor()

# Création des tables pour l'inventaire et la consultation du stock
c.execute('''
    CREATE TABLE IF NOT EXISTS inventory (
        lot TEXT PRIMARY KEY,
        code_article TEXT,
        poids_physique REAL,
        remarque TEXT
    )
''')

c.execute('''
    CREATE TABLE IF NOT EXISTS stock_consultation (
        code_article TEXT,
        magasin TEXT,
        lot TEXT PRIMARY KEY,
        utilisation_libre INTEGER,
        valeur_utilisation_libre REAL,
        bloque INTEGER,
        designation_article TEXT
    )
''')
conn.commit()

# Fonction pour décomposer le code-barres
def parse_barcode(barcode):
    barcode = barcode.strip()
    if len(barcode) == 28:
        code_article = barcode[8:18]  # Extraction du code article
        lot = barcode[18:]            # Extraction du lot
        return code_article, lot
    else:
        st.warning("Code-barres invalide. Veuillez entrer un code-barres de 28 caractères.")
        return None, None

# Fonction pour charger et afficher les données du fichier Excel
def load_excel(file):
    df = pd.read_excel(file)
    return df

# Fonction pour insérer les données de stock dans la base de données
def insert_stock_data(conn, df):
    c = conn.cursor()
    for _, row in df.iterrows():
        try:
            c.execute('''
                INSERT INTO stock_consultation (code_article, magasin, lot, utilisation_libre, valeur_utilisation_libre, bloque, designation_article)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (row["Code Article"], row["Magasin"], row["Lot"], row["A utilisation libre"], float(row["Val. utilis. libre"]), row["Bloqué"], row["Désignation article"]))
            conn.commit()
        except sqlite3.IntegrityError:
            st.warning(f"Le lot {row['Lot']} existe déjà dans la base de données et n'a pas été inséré.")

# Fonction pour réinitialiser le stock
def reset_stock(conn):
    c = conn.cursor()
    c.execute("DELETE FROM stock_consultation")
    conn.commit()
    st.success("Stock réinitialisé avec succès.")

# Interface utilisateur
st.title("Gestion de l'Inventaire et Consultation du Stock")

# Menu de navigation pour basculer entre les deux parties
menu = ["Inventaire", "Consultation du Stock"]
choice = st.sidebar.selectbox("Choisir une option", menu)

if choice == "Inventaire":
    st.subheader("Gestion de l'Inventaire")

    # Choisir entre Scan ou Saisie Manuelle
    option = st.selectbox("Choisir une méthode d'entrée", ["Scanner un code-barres", "Saisie manuelle"])

    if option == "Scanner un code-barres":
        # Champs de saisie pour le scan
        barcode_input = st.text_input("Scan or Enter Barcode", key="barcode_input")
        poids_bobine = st.number_input("Poids Physique (en kg)", min_value=0.0, step=0.01)
        remarque = st.text_input("Remarque", key="remarque")

        if barcode_input:
            code_article, lot = parse_barcode(barcode_input)
            if code_article and lot:
                if st.button("Enregistrer"):
                    try:
                        # Insertion dans la base de données
                        c.execute("INSERT INTO inventory (lot, code_article, poids_physique, remarque) VALUES (?, ?, ?, ?)",
                                  (lot, code_article, poids_bobine, remarque))
                        conn.commit()
                        st.success(f"Lot: {lot}, Code Article: {code_article}, Poids: {poids_bobine} kg - enregistré avec succès.")
                        # Réinitialiser les champs après l'enregistrement
                        st.experimental_rerun()
                    except sqlite3.IntegrityError:
                        st.error("Erreur : Le lot existe déjà dans la base de données.")

    elif option == "Saisie manuelle":
        # Champs de saisie manuelle
        lot_input = st.text_input("Entrer le Lot")
        code_article_input = st.text_input("Entrer le Code Article")
        poids_bobine = st.number_input("Poids Physique (en kg)", min_value=0.0, step=0.01)
        remarque = st.text_input("Remarque", key="remarque")

        if lot_input and code_article_input:
            if st.button("Enregistrer Manuellement"):
                try:
                    # Insertion dans la base de données
                    c.execute("INSERT INTO inventory (lot, code_article, poids_physique, remarque) VALUES (?, ?, ?, ?)",
                              (lot_input, code_article_input, poids_bobine, remarque))
                    conn.commit()
                    st.success(f"Lot: {lot_input}, Code Article: {code_article_input}, Poids: {poids_bobine} kg - enregistré avec succès.")
                    # Réinitialiser les champs après l'enregistrement
                    st.experimental_rerun()
                except sqlite3.IntegrityError:
                    st.error("Erreur : Le lot existe déjà dans la base de données.")

    # Options dans la barre latérale
    st.sidebar.subheader("Rechercher dans l'inventaire")
    search_option = st.sidebar.selectbox("Rechercher par", ["Lot", "Code Article"])
    search_input = st.sidebar.text_input("Entrez votre recherche", key="search_input")

    if search_input:
        if search_option == "Lot":
            query = "SELECT lot AS 'Lot', code_article AS 'Code Article', poids_physique AS 'Poids Physique', remarque AS 'Remarque' FROM inventory WHERE lot LIKE ?"
            params = ('%' + search_input + '%',)
        elif search_option == "Code Article":
            query = "SELECT lot AS 'Lot', code_article AS 'Code Article', poids_physique AS 'Poids Physique', remarque AS 'Remarque' FROM inventory WHERE code_article LIKE ?"
            params = ('%' + search_input + '%',)

        searched_data = c.execute(query, params).fetchall()

        if searched_data:
            df = pd.DataFrame(searched_data, columns=["Lot", "Code Article", "Poids Physique", "Remarque"])
            st.table(df)
        else:
            st.write("Aucun résultat trouvé.")

    # Option de modification ou suppression
    st.sidebar.subheader("Modifier ou supprimer une entrée")
    action = st.sidebar.selectbox("Choisir une action", ["Modifier", "Supprimer"])

    lot_to_modify_or_delete = st.sidebar.text_input("Entrez le Lot")

    if action == "Modifier":
        new_code_article = st.sidebar.text_input("Nouveau Code Article")
        new_poids_bobine = st.sidebar.number_input("Nouveau Poids Physique (en kg)", min_value=0.0, step=0.01)
        new_remarque = st.sidebar.text_input("Nouvelle Remarque")

        if st.sidebar.button("Mettre à jour"):
            c.execute('''
                UPDATE inventory
                SET code_article = ?, poids_physique = ?, remarque = ?
                WHERE lot = ?
            ''', (new_code_article, new_poids_bobine, new_remarque, lot_to_modify_or_delete))
            conn.commit()
            st.success(f"Lot {lot_to_modify_or_delete} mis à jour avec succès.")
            st.experimental_rerun()

    elif action == "Supprimer":
        if st.sidebar.button("Supprimer"):
            c.execute('DELETE FROM inventory WHERE lot = ?', (lot_to_modify_or_delete,))
            conn.commit()
            st.success(f"Lot {lot_to_modify_or_delete} supprimé avec succès.")
            st.experimental_rerun()

    # Affichage des données stockées
    st.subheader("Tous les codes-barres scannés")
    scanned_data = c.execute("SELECT lot AS 'Lot', code_article AS 'Code Article', poids_physique AS 'Poids Physique', remarque AS 'Remarque' FROM inventory").fetchall()

    if scanned_data:
        df = pd.DataFrame(scanned_data, columns=["Lot", "Code Article", "Poids Physique", "Remarque"])
        st.table(df)
    else:
        st.write("Aucun code-barres scanné pour le moment.")

elif choice == "Consultation du Stock":
    st.subheader("Consultation du Stock")

    # Vérifier si le stock existe déjà
    c.execute("SELECT COUNT(*) FROM stock_consultation")
    stock_exists = c.fetchone()[0] > 0

    if not stock_exists:
        uploaded_file = st.file_uploader("Choisissez un fichier Excel", type=["xlsx", "xls"])
        if uploaded_file:
            df = load_excel(uploaded_file)
            st.write("Données du fichier Excel chargées :")
            st.dataframe(df)

            # Extraction des colonnes spécifiques
            columns_to_extract = ["Code Article", "Magasin", "Lot", "A utilisation libre", "Val. utilis. libre", "Bloqué", "Désignation article"]
            extracted_df = df[columns_to_extract]

            st.write("Données extraites :")
            st.dataframe(extracted_df)

            if st.button("Valider"):
                insert_stock_data(conn, extracted_df)
                st.success("Données du stock enregistrées dans la base de données.")
                st.experimental_rerun()

    else:
        search_input = st.text_input("Recherche dans le stock")

        if search_input:
            query = """
            SELECT code_article AS 'Code Article', magasin AS 'Magasin', lot AS 'Lot', utilisation_libre AS 'A utilisation libre', 
            valeur_utilisation_libre AS 'Val. utilis. libre', bloque AS 'Bloqué', designation_article AS 'Désignation article'
            FROM stock_consultation
            WHERE code_article LIKE ? OR lot LIKE ? OR designation_article LIKE ?
            """
            params = ('%' + search_input + '%', '%' + search_input + '%', '%' + search_input + '%')

            searched_data = c.execute(query, params).fetchall()

            if searched_data:
                df = pd.DataFrame(searched_data, columns=["Code Article", "Magasin", "Lot", "A utilisation libre", "Val. utilis. libre", "Bloqué", "Désignation article"])
                st.table(df)
            else:
                st.write("Aucun résultat trouvé.")

        if st.button("Réinitialiser Stock"):
            reset_stock(conn)
            st.experimental_rerun()


# Fermeture de la connexion à la base de données
conn.close()
