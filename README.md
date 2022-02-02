# Projet 10 : développement d'un chatbot pour réservation de voyage <br>

- Chatbot minimaliste , modèle de compréhension de langage clé-en-main fourni par le service cognitif LUIS (Azure) et entraîné avec le dataset Frames - 5 paramètres : date et aéroport d'origine et de destination, budget
- Basé sur les librairies python du BotFramework v4 de ms Azure et servi à l'aide du framework aiohttp
- Le dossier Models contient 2 notebooks contenant les classes d'entraînement et d'évaluation du modèle de compréhension de langage, ainsi qu'un notebook d'analyse exploratoire du dataset
- La classe LUISTrainer v1 crée et teste un modèle uniquement basé sur la reconnaissance d'entités, la v2 crée un modèle combinant de multiples intentions et entités
- Le chatbot v1 a une logique minimale, la v2 a une logique conditionnelle plus poussée et la v3 enrichit le monitoring en production via Opencensus et Azure Application Insights
- Une série de tests unitaires et fonctionnels a été définie dans le dossier tests
<br><br>
Les grandes lignes du projet sont données dans dans la présentation ppt<br><br>
