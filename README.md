# 26INF1103P5-4 INF1103 Project

## Yapalyzer - An Automated Triage System for Ride-Hailing Reports

## Installation
### Dependencies and Requirements
A `.env` file must be placed in the project root directory, containing a valid API key for Google Gemini. 
**Without this API key, the program will not run**.

> ```GEMINI_API_KEY=AQ.thisisarandomstringwithletterss-iwanticecreammmmmm```


### Manual Docker setup guide
1) Run the following command in the project root directory. (Remember the `.`!)
    > ```docker image build -t <image_name> .```

2) Start the container using the following command. Make sure to use the same image name as above
    > ```docker run --rm -it --env-file .env -v ./logs_reports:/app/logs_reports <image_name>```

### Less Manual Docker setup guide
1) Run the following code to automatically build the image and run the container
    > ```docker compose run --rm yapalyzer```


## Initial Commit Guide
Before you start working on your own section, please do the following:
1) ```git pull``` to make sure you have the latest version of the repository

2) ```git branch <your_section>```
For `<section>`, input your assigned role. For example, if I am doing IO Manager, I'll put `git branch io_manager`.
This will be the branch you're working on

4) ```git checkout <your_section>```
Navigate to your new branch using this command

5) ```git branch```
verify you're on the correct branch using this command. Your output should show something like:
> ```
> main
> * io_manager
> ```

6) After this, you can start work, and git add/commit/push as you normally would.

7) Once you're done with your work (as in you have NOTHING else to add or change), **create a pull request on the GitHub page**.
