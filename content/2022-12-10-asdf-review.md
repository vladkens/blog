---
title: asdf — a good tool to manage python, node, etc runtime
slug: asdf-package-manager
date: 2022-12-10
taxonomies:
  tags: ["tools"]
---

When you develop or maintain many projects or use a microservice architecture, over time you have a zoo of different programming languages and their versions on your computer. Each service has its own dependencies. After a while it becomes hellishly difficult to work comfortably.

Initially, I controlled runtimes versions through homebrew, switching them when needed. Later I switched to nvm for NodeJS, pyenv for Python. If you add to this tools[ automatic version selection](https://github.com/vladkens/zsh-auto-nvm-use) on cd to project folder, it becomes almost comfortable. But this solution in the terminal is visually slow.

I was looking for alternatives and found an amazing tool with a strange name – [asdf](https://asdf-vm.com/). This is single cli-tool for managing multiple runtimes and their versions. Each runtime is added via plugins and there are already about [450 of them](https://github.com/asdf-vm/asdf-plugins).

asdf itself knows how to install different versions, can switch runtime when directory changed and works fast.

## Installation

On MacOS you can install asdf with homebrew (for other OS follow [official guide](https://asdf-vm.com/guide/getting-started.html)):

```sh
brew install asdf
```

After that we can set the necessary runtimes:

```sh
# Install NodeJS
asdf plugin-add nodejs
asdf install nodejs latest:16
asdf install nodejs latest:14

# Install Python
asdf plugin-add python
asdf install python latest:3.10
asdf install python latest:3.11

# Also possible to get list of available versions for inslation
asdf list all nodejs
asdf list all python

# Or list of already installed versions
asdf list nodejs
asdf list python

# Get current selected runtimes
asdf current

# Set global runtime (will create a .tool-versions in root of user directory)
asdf global nodejs latest:16
asdf global python latest:3.10

# Or set local runtime (will create a .tool-versions file in current directory)
asdf local nodejs latest:14
asdf local python latest:3.10
```

## Version select on directory change

`asdf` can also automatically select the correct version depending on the current directory and will do this on each `cd`. It does this by going up in the hierarchy until it finds version of required runtime in the `.tool-versions` file.

This allows flexible control over multiple versions of runtimes in each folder. For example you have an old project where tooling is written in python 3.8, you want to start code a new microservice in python 3.11, and globally in the system you are using version 3.9. `asdf` will handle it for you!

To enable this auto version select feature add next line to your shell rc-file (for more options or other shells see [official guide](https://asdf-vm.com/guide/getting-started.html#_3-install-asdf)):

```sh
# For zsh (~/.zhsrc)
. $(brew --prefix asdf)/libexec/asdf.sh

# For fish-shell (~/.config/fish/config.fish)
source "(brew --prefix asdf)"/libexec/asdf.fish
```

That’s all. Now just make a cd to the project folder and set the required runtime version. Now when you navigate to the project folder, asdf will automatically select python of this version. You can check selected versions with:

```sh
# for example install global python version
asdf global python latest:3.11

# go to project folder
cd ~/some_project

# install reqired python version (will create or update .tool-versions file)
asdf local python latest:3.10

# see current active runtime versions (should be 3.10)
asdf current

# check python version (should be same)
python --version

# go back to user folder
cd ~

# check python version again (should be 3.11)
asdf current
python --version
```

Also you can commit the `.tool-versions` file directly into GIT. So then all team members will also know what versions of runtimes is in use for that service.

## One more life story

Using asdf you can manage not only runtime language versions, but also cli tools such as aws-cli, terraform, kubectl.

So if you have different versions of Kubernetes clusters, even the official documentation does not recommend using more than one version of difference.

Using multiple versions via brew is not convenient (you have to switch versions manually all the time). But these cli tools can also be put in `.tool-versions`.

```sh
asdf plugin-add kubectl https://github.com/asdf-community/asdf-kubectl.git

asdf install kubectl latest:1.20
asdf install kubectl latest:1.25

asdf global kubectl latest:1.25

cd ~/legacy_project
asdf local kubectl latest:1.20
```

---

That’s all for now. If this information was helpful to you, don’t forget to subscribe to receive notifications of new posts.
