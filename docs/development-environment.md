# Set up Development Environment

You'll need to set up a development environment if you want to develop a new feature or component
for diyHue. Read on to learn how to set up.

## Developing with Visual Studio Code + devcontainer

The easiest way to get started with development is to use Visual Studio Code with devcontainers.
This approach will create a preconfigured development environment with all the tools you need.
(Learn more about devcontainers)[https://code.visualstudio.com/docs/devcontainers/containers]

### Prerequisites

* (Docker)[https://docs.docker.com/get-docker/]
* (Visual Studio Code)[https://code.visualstudio.com/]
* (Git)[https://git-scm.com/]

### Getting started

1. Go to (diyHue repository)[https://github.com/diyhue/diyHue] and click _fork_.
2. Once your fork is created, clone the repository to your local environment.
3. Open the cloned folder in Visual Studio Code
4. Run the Dev Containers: Open Folder in Container... command from the Command Palette (F1) or
   quick actions Status bar item.
   (More information can be found in the official documentation)[https://code.visualstudio.com/docs/devcontainers/containers]
5. The Dev Container image will then be built (this may take a few minutes), after this your
   development environment will be ready.

In the future, if you want to get back to your development environment: open Visual Studio Code,
click on the "Remote Explorer" button in the sidebar, select "Containers" at the top of the sidebar.

## Setup Local Repository

 Go to (diyHue repository)[https://github.com/diyhue/diyHue] and click _fork_. Once forked, setup
 your local copy of the source using the commands:

 ```
 git clone https://github.com/YOUR_GIT_USERNAME/diyHue.git
 cd diyHue
 git remote add upstream https://github.com/diyhue/diyHue.git
 ```

 install the requirements with a provided script named `setup`.

 ```
 script/setup
 ```

 This will create a virtual environment and install all necessary requirements. You're now set!

 Each time you start a new terminal session, you will need to activate your virtual environment:

 ```
 source venv/bin/activate
 ```

 After that you can run diyHue like this:

```
diyhue -c config
```

The diyHue configuration is stored in the `config` directory in your repository.

