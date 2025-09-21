import json
import logging
import os
import uuid

from azure.cosmos import CosmosClient
from azure.functions import AuthLevel, FunctionApp, HttpRequest, HttpResponse, Out, Document, HttpMethod
from azure.storage.blob import PublicAccess
from azure.storage.blob.aio import ContainerClient

app = FunctionApp(http_auth_level=AuthLevel.ANONYMOUS)

@app.route(route="upload", methods=[HttpMethod.POST])
async def fnPostDataStorage(req: HttpRequest) -> HttpResponse:
    logging.info("Processing the image in storage")

    try:
        if not req.headers.get("file-type"):
            logging.warning("User did not set file-type header")
            return HttpResponse("The file-type header is mandatory", status_code=400)

        file_type = req.headers.get("file-type")
        file = req.files["file"]

        if not file:
            if not file:
                logging.warning("The user did not uploaded any file")
            else:
                logging.warning("The user uploaded an empty file")

            return HttpResponse("The file was not sent or is empty", status_code=400)

        connection_string = os.getenv("AzureWebJobsStorage", "")
        container_name = file_type
        blob_name = file.filename

        async with ContainerClient.from_connection_string(connection_string, container_name) as container_client:
            if not await container_client.exists():
                await container_client.create_container(public_access=PublicAccess.CONTAINER)

            async with container_client.get_blob_client(blob_name) as blob_client:
                await blob_client.upload_blob(file.stream, overwrite=True)
        

        logging.info(f"File {file.filename} stored successfully")

        return HttpResponse(json.dumps({"message":f"Arquivo {file.filename} armazenado com sucesso", "blobUri": blob_client.url}))
    except Exception as e:
        logging.error(f"Error: Failed to store file. " + str(e.with_traceback(None)))
        print(e)
        return HttpResponse(f"Erro ao tentar armazenar o arquivo", status_code=500)
    
@app.cosmos_db_output(arg_name="doc", database_name=os.getenv("DatabaseName", ""), container_name=os.getenv("ContainerName", ""), connection="CosmosDBConnection", create_if_not_exists=True, partition_key="id")
@app.route(route="movies", methods=[HttpMethod.POST])
def fnPostDatabase(req: HttpRequest, doc: Out[Document]) -> HttpResponse:
    logging.info("Adding new movie to CosmosDB")
    content = req.get_body()

    try:
        movie_id = uuid.uuid4().hex 
        movie = json.loads(content)
        movie["id"] = movie_id
        doc.set(Document.from_dict(movie))
    except json.JSONDecodeError as e:
        logging.warning("Error: The user did not send the movie data in JSON format. " + str(e.with_traceback(None)))
        return HttpResponse(f"Os dados do filme devem ser enviados no formato JSON", status_code=400)
    except Exception as e:
        logging.error("Error: Failed to save movie data. " + str(e.with_traceback(None)))
        return HttpResponse(f"Erro ao enviar dados do filme", status_code=500)
    else:
        logging.info("The movie data was saved successfully")
        return HttpResponse(f"Dados do filme enviados com sucesso")
    
@app.route(route="movies/{id}", methods=[HttpMethod.GET])
async def fnGetMovieDetails(req: HttpRequest) -> HttpResponse:
    logging.info("Getting movie details from CosmosDB")

    id_movie = req.route_params["id"]

    if not id_movie:
        logging.warning("Error: The user did not send the movie id")
        return HttpResponse(f"O id do filme é necessário para encontrá-lo", status_code=400)

    cosmos_db_uri = os.getenv("CosmosDBUri", "")
    cosmos_db_account_key = os.getenv("CosmosDBAccountKey", "")
    cosmos_db_database_name = os.getenv("DatabaseName", "")
    database_container_name = os.getenv("ContainerName", "")

    cosmos_client = CosmosClient(cosmos_db_uri, cosmos_db_account_key)
    cosmos_db_database = cosmos_client.get_database_client(cosmos_db_database_name)
    movies_container = cosmos_db_database.get_container_client(database_container_name)
    query = f"SELECT * FROM c WHERE c.id = '{id_movie}'"
    movies = []

    result = movies_container.query_items(query=query)

    for movie in result:
        movies.append(movie)

    logging.info("The movie data was retrieved successfully")

    if len(movies) > 0:
        return HttpResponse(json.dumps(movies[0]))
    else:
         return HttpResponse('{"error": "Filme não encontrado"}', status_code=404)
    
@app.route(route="movies", methods=[HttpMethod.GET])
async def fnGetAllMovies(req: HttpRequest) -> HttpResponse:
    logging.info("Getting all movies from CosmosDB")

    cosmos_db_uri = os.getenv("CosmosDBUri", "")
    cosmos_db_account_key = os.getenv("CosmosDBAccountKey", "")
    cosmos_db_database_name = os.getenv("DatabaseName", "")
    database_container_name = os.getenv("ContainerName", "")

    cosmos_client = CosmosClient(cosmos_db_uri, cosmos_db_account_key)
    cosmos_db_database = cosmos_client.get_database_client(cosmos_db_database_name)
    movies_container = cosmos_db_database.get_container_client(database_container_name)
    query = f"SELECT * FROM c"
    movies = []

    result = movies_container.query_items(query=query, enable_cross_partition_query=True)

    for movie in result:
        movies.append(movie)

    logging.info("The movies were retrieved successfully")

    if len(movies) > 0:
        return HttpResponse(json.dumps(movies))
    else:
         return HttpResponse('{"message": "Nenhum filme disponível"}')