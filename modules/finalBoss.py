import os
import json
import numpy as np
from pymongo import MongoClient
from scipy.spatial.distance import cosine, euclidean, minkowski
from sklearn.preprocessing import normalize
from sentence_transformers import SentenceTransformer
import time

# loads the SBERT model
model = SentenceTransformer('bert-base-nli-mean-tokens')

def calculateSimilarity(userEmbedding, trainEmbeddings):
    # normalizes the embeddings
    userEmbedding = normalize(userEmbedding.reshape(1, -1))
    trainEmbeddings = normalize(trainEmbeddings)

    # calculates cosine similarity, angular distance, Euclidean distance, and Minkowski distance
    cosineSimilarity = np.dot(userEmbedding, trainEmbeddings.T).flatten()
    angularDistance = (np.arccos(cosineSimilarity) / np.pi).flatten()
    euclideanDistance = np.linalg.norm(userEmbedding - trainEmbeddings, ord=2, axis=1).flatten()
    minkowskiDistance = np.linalg.norm(userEmbedding - trainEmbeddings, ord=2, axis=1).flatten()

    return cosineSimilarity, angularDistance, euclideanDistance, minkowskiDistance


def finalBoss(rawArticle, lemmatizedArticle):
    # connects to the MongoDB database
    client = MongoClient("mongodb://localhost:27017/")
    db = client["blockchain_db"]
    collection = db["chain"]

    db_name = "blockchain_db"
    collection_name = "chain"

    # Check if the database and collection exist and if the connection is successful
    if db.command("ping")["ok"] == 1 and db_name in client.list_database_names() and collection_name in db.list_collection_names():
        print(" \n Connection to the blockchain database successful")
        ("Processing, please wait")
        start_time = time.time()
    else:
        print("Could not establish a connection with the blockchain DB or collection does not exist")
        print ("Scrap news articles from the website using option '1' of the main menu to load information into the blockchain DB \n")
        input("Press ENTER to continue")
        return

    # retrieves the normalized bodies of all articles from the database
    trainArticles = list(collection.find({}, {"_id": 0, "article_title": 1, "article_link": 1, "normalized_body": 1}))

    # converts the user's article to a 768-dimensional embedding using SBERT
    userEmbedding = model.encode([lemmatizedArticle])[0]

    # converts the train articles to embeddings using SBERT
    trainEmbeddings = model.encode([article["normalized_body"] for article in trainArticles])

    # calculates similarity between the user's article and the articles in the database
    cosineSimilarity, angularDistances, euclideanDistances, minkowskYDistances = calculateSimilarity(userEmbedding, trainEmbeddings)

    # finds the indices of the top 5 most similar articles for each distance measure
    cosineTopIndices = np.argsort(cosineSimilarity)[::-1][:5]
    angularTopIndices = np.argsort(angularDistances)[:5]
    euclideanTopIndices = np.argsort(euclideanDistances)[:5]
    minkowskiTopIndices = np.argsort(minkowskYDistances)[:5]

    # gets the titles, links, and bodies of the top 5 most similar articles for each distance measure
    cosineTopArticles = [{"article": trainArticles[int(idx)], "similarity": float(similarity)} for idx, similarity in zip(cosineTopIndices, cosineSimilarity[cosineTopIndices])]
    angularTopArticles = [{"article": trainArticles[int(idx)], "similarity": float(similarity)} for idx, similarity in zip(angularTopIndices, angularDistances[angularTopIndices])]
    euclideanTopArticles = [{"article": trainArticles[int(idx)], "similarity": float(similarity)} for idx, similarity in zip(euclideanTopIndices, euclideanDistances[euclideanTopIndices])]
    minkowskiTopArticles = [{"article": trainArticles[int(idx)], "similarity": float(similarity)} for idx, similarity in zip(minkowskiTopIndices, minkowskYDistances[minkowskiTopIndices])]

    # sorts the articles by highest to lowest similarity
    cosineTopArticles = sorted(cosineTopArticles, key=lambda x: x["similarity"], reverse=True)
    angularTopArticles = sorted(angularTopArticles, key=lambda x: x["similarity"])
    euclideanTopArticles = sorted(euclideanTopArticles, key=lambda x: x["similarity"])
    minkowskiTopArticles = sorted(minkowskiTopArticles, key=lambda x: x["similarity"])

    # finds the common articles in all four calculations
    commonResults = []
    cosineCommon = [article["article"]["article_link"] for article in cosineTopArticles]
    angularCommon = [article["article"]["article_link"] for article in angularTopArticles]
    euclideanCommon = [article["article"]["article_link"] for article in euclideanTopArticles]
    minkowskyCommon = [article["article"]["article_link"] for article in minkowskiTopArticles]

    commonLinks = list(set(cosineCommon) & set(angularCommon) & set(euclideanCommon) & set(minkowskyCommon))
    
    for link in commonLinks:
        cosineResults = next(item for item in cosineTopArticles if item["article"]["article_link"] == link)["similarity"]
        angularResults = next(item for item in angularTopArticles if item["article"]["article_link"] == link)["similarity"]
        euclideanResults = next(item for item in euclideanTopArticles if item["article"]["article_link"] == link)["similarity"]
        minkowskiResults = next(item for item in minkowskiTopArticles if item["article"]["article_link"] == link)["similarity"]
        averageResults = (cosineResults + (1 - angularResults) + (1 - euclideanResults) + (1 - minkowskiResults)) / 4  # Average of adjusted scores
        commonResults.append({"article_link": link, "average_score": averageResults})

    # sorts the articles by highest average score
    orderedArticles = sorted(commonResults, key=lambda x: x["average_score"], reverse=True)

    end_time = time.time()
    elapsed_time = end_time - start_time

    # prints the article with the highest average score
    if orderedArticles:
        highestArticle = orderedArticles[0]
        if highestArticle["average_score"] < 0.6:
            print("Warning: The score of the highest article is below 0.6. This is not considered a high enough score, article is shown for debbuging only")
        print("Top Article Link:", highestArticle["article_link"])
        print("Top Average Score:", highestArticle["average_score"])
        print(f"Elapsed time: {elapsed_time:.4f} seconds")
        input("Press ENTER to continue")

    # saves the results to JSON files
    output_Directory = "output Files"
    os.makedirs(output_Directory, exist_ok=True)

    with open(os.path.join(output_Directory, "1clashAllcosine_similarity.json"), "w") as f:
        json.dump(cosineTopArticles, f, indent=4)

    with open(os.path.join(output_Directory, "1clashAllangular_distance.json"), "w") as f:
        json.dump(angularTopArticles, f, indent=4)

    with open(os.path.join(output_Directory, "1clashAlleuclidean_distance.json"), "w") as f:
        json.dump(euclideanTopArticles, f, indent=4)

    with open(os.path.join(output_Directory, "1clashAllminkowski_distance.json"), "w") as f:
        json.dump(minkowskiTopArticles, f, indent=4)

    return None