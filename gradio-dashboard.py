import pandas as pd
import numpy as np

from dotenv import load_dotenv

from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
import pandas as pd

import gradio as gr
import os


load_dotenv()

books = pd.read_csv("book_with_emotions.csv")

books["large_thumbnail"] = books["thumbnail"] + "&fife=w800"
books["large_thumbnail"] = np.where(books["large_thumbnail"].isna(),"cover_not_found.jpg",books["large_thumbnail"])


if os.path.exists("description_embeddings"):

    db_books = Chroma(persist_directory="description_embeddings", embedding_function=OpenAIEmbeddings())

else:

    loader = TextLoader("tagged_description.txt", encoding="utf-8")
    raw_documents = loader.load()
    text_splitter = CharacterTextSplitter(chunk_size=0, chunk_overlap=0, separator="\n")
    documents = text_splitter.split_documents(raw_documents)

    db_books = Chroma.from_documents(documents,embedding=OpenAIEmbeddings(),persist_directory="description_embeddings")



def retreive_semantice_recommendations(query: str, category:str, tone: str, initial_top_k: int = 16, final_top_k :int = 50 ) -> pd.DataFrame:

    recs = db_books.similarity_search(query, k=initial_top_k)

    books_list = []

    # for finding out the sentiment
    for rec in recs:
        # '"' helps split out the quotation marks
        books_list.append(int(rec.page_content.strip('"').split(" ")[0]))

    book_recs = books[books["isbn13"].isin(books_list)].head(final_top_k)

    # for Categories
    if category != "ALL":
        # retrieve recommendations to final top k
        book_recs = book_recs[book_recs["simple_category_mapping"] == category][:final_top_k]

    else:

        book_recs = book_recs.head(final_top_k)

    # For tonality
    if tone == "Happy":

        book_recs.sort_values(by="joy", ascending=False, inplace=True)

    elif tone == "Surprising":

        book_recs.sort_values(by="surprise", ascending=False, inplace=True)

    elif tone == "Angry":

        book_recs.sort_values(by="anger", ascending=False, inplace=True)

    elif tone == "Suspenseful":

        book_recs.sort_values(by="fear", ascending=False, inplace=True)

    elif tone == "Sadness":

        book_recs.sort_values(by="sadness", ascending=False, inplace=True)

    return book_recs


# retreive_semantice_recommendations("A book on exercises",10)

def recommend_books(
    query:str,
    category:str,
    tone:str,
):

    recommendations = retreive_semantice_recommendations(query, category, tone)
    results = []

    for _,row in recommendations.iterrows():

        description = row["description"]

        trunc_desc_split = description.split()

        # join with just 30 words
        truncated_desc = " ".join(trunc_desc_split[:30])

        try:
            
            authors_split = row["authors"].split(";")

        except:
            
            print("no author split")

        if len(authors_split) == 2:

            authors = f"{authors_split[0]} and {authors_split[1]}"

        elif len(authors_split) > 2:
            # use single instead of double
            authors = f"{', '.join(authors_split[:-1])}, and {authors_split[-1]}"

        else:
            authors = row["authors"]

        #  Creating the Captions for the Dashboard

        caption = f"{row['title_and_subtitle']} by {authors} : {truncated_desc}"

        results.append((row["thumbnail"], caption))

    return results

# creating the dropdowns

categories = ["ALL"] + sorted(books["simple_category_mapping"].unique())
tones = ["ALL"] + ["Happy","Angry","Surprising","Suspenseful","Sadness"]

with gr.Blocks(theme = gr.themes.Glass()) as dashboard:

    gr.Markdown("# Semantic Book Recommender")

    with gr.Row():

        user_query = gr.Textbox(label = "Please enter a description of a book",
                                placeholder = "eg. A story about friendships")
        # default value all
        category_dropdown = gr.Dropdown(choices = categories, label = "Select a Category", value = "ALL")

        tone_dropdown = gr.Dropdown(choices = tones,label = "Select a Emotional Tone", value = "ALL")

        submit_button = gr.Button("Find Recommendation")

    gr.Markdown("## Recommendations")

    output = gr.Gallery(label = "Recommend books", columns=8, rows =2)

    submit_button.click(fn = recommend_books, inputs = [user_query, category_dropdown, tone_dropdown],
                        outputs = output )



    if __name__ == "__main__":

            dashboard.launch()






