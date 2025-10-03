This is a generative ai chatbot that almost will answer all the questions the user asked . It uses JSON files to store user data and chat history. To improve efficient of answer retriving, I used Cache concept in this code.


USE ANACONDA COMMAND PROMPT FOR WHOLE THIS PROCESS


INSTALL NEEDED LIBRARIES TO RUN THIS CODE:
_________________________________________

first you have to download Ollama in this web address -> https://ollama.com/download

and then pull the LLAMA3 language model using this command -> ollama pull llama3 

after pull llama3 you have to run it using -> ollama run llama3



NEEDED LIBRARIES:
________________

pip install streamlit langchain langchain-community fuzzywuzzy python-Levenshtein

you should give your stability api key for image generation at 93rd line --> api_key = os.getenv("STABILITY_API_KEY", "YOUR-API-HERE")





IF ALL SET YOU HAVE TO GO TO THE COMMAND PROMPT AND CHANGE DIRECTORY PATH TO YOUR FILE EXISTED FOLDER (Nbot.py) THEN RUN -> streamlit run Nbot.py


