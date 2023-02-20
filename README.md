<br/>
<h2 align="center">
    <p align="center">
        <img src="img/BXplorer_Logo.png" alt="BXplorer Logo" width="230" height="180">
    </p>
    A JupyterLab extension that provides a UI to operate objects in a cloud storage service.
</h2>
<br/>

# Contents

- [Why?](#why)
- [Installation](#installation)
- [Usage](#usage)
- [Current Status](#current-status)
- [Want to contribute?](#want-to-contribute)
- [Found an issue? Have suggestions?](#issues-and-suggestions)
- [Licensing](#licensing)
- [Notes](#notes-for-your-consideration)

<br/>

### Why?

We have created BXplorer after reviewing other JupyterLab extensions to operate objects in cloud storage services (Google, Azure, AWS). The exntesions we have reviewed work really well. After making an inventory of the changes we might need to do in some of them we realized that we would basically need to modify them so much that we might end up with an entirely new extension and/or modifying JupyterLab's FileBrowser component and end up with a customized version so we decided to start from scratch and offer this new extension to the community hoping it is useful.

We wanted to use a different approach handling AWS credentials. We also wanted to show more information such as object size, modification date, cross account buckets (AWS), etc.

<br/>

### Installation

We are working on having a package in PyPi available. At the moment you can do the following:

```bash
git clone https://github.com/Navteca/jupyterlab-bxplorer.git
cd jupyterlab-bxplorer/
npm install
python -m build
pip install jupyterlab_bxplorer-<version>-py3-none-any.whl
```

<br/>
if the installation process runs successfully, check if the extension has been activated:

```
jupyter labextension list
jupyter serverextension list
```

<br/>
If not, you might need to run:

```
jupyter labextension enable --py jupyterlab_bxplorer
jupyter serverextension enable --py jupyterlab_bxplorer
```

<br/>

### Usage

Once the extension is installed, you will notice a new small telescope icon on the left panel. Cliking on it will expand the panel and you will notice 3 tabs: Private, Public and Favorites.

- **Private:** will list all the buckets your AWS Credentials, Role/Service Account give your access to.
- **Public:** shows also a dropdown with a few options (AWS, Google, Microsoft) when selecting any of those options you will notice the list of cloud storage objects shown changes. The extension pulls the information from those public repositories.
- **Favorites:** is used to keep those cloud storage objects you want to have acess to quickly. Additionally you can add external objects

The extension will take the AWS credentials as described [here](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html). In one of our instances we use an AWS Role with a Service Account which makes it easier to manage permissions and so on.

There are a few ways of configuring the AWS Credentials in a Linux and Linux-like environments:

- [Environment Variables](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-envvars.html)
- [CLI Credentials file](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html) and [Configurations file](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)
- If you are launching your JupyterLab instance as a pod in K8S you can also use an AWS Role connected to a Service Account as an environment variable, the extension will also use it.

In the `Favorites` tab there is a button `Add bucket` that allows you to add a cross-account bucket. These are buckets that per default will not appear in the `Private` tab because they belogn to another account.

<br/>

### Current Status

We are in a very early stage in terms of all the features we want to add to the extension to be even with other extensions. Currently you can do the following:

- List private storage objects
  - [x] AWS
  - [ ] Google
  - [ ] Azure
- List public storage objects
  - [x] AWS
  - [ ] Google
  - [ ] Azure
- Add external/cross-account storage objects to Favorites list
  - [x] AWS
  - [ ] Google
  - [ ] Azure
- [x] Removing storage objects from Favorites list
- Downloading storage objects
  - [x] AWS
  - [ ] Google
  - [ ] Azure
- Show cross-account storage objects
  - [x] AWS
  - [ ] Google
  - [ ] Azure
- Show storage object's information (metadata)
  - [x] AWS
  - [ ] Google
  - [ ] Azure
- [x] Show downloads panel
- [ ] Automatic update of downloads panel
- [ ] Responsiveness improvements of both Browser and Downlaods panel
- Copy storage object path
  - [ ] AWS
  - [ ] Google
  - [ ] Azure
- Upload object to a storage object
  - [ ] AWS
  - [ ] Google
  - [ ] Azure
- [ ] Tests
- [ ] Documentation

<br/>

### Want to contribute?

First of all, thank you for taking the time to contribute!

Do you find this extension useful, with potential to be great and you like writing code? Please, don't hesitate to contribute. There is so much to do from improving an already existing feature, implement a new one, etc.

There are a couple ways you can contribute to the extension:

- [Opening issues](https://github.com/Navteca/jupyterlab-bxplorer/issues): you can open an issue either to report a bug, request an enhancement, ask a question, suggest a new feature, etc.
- [Pull Requests](https://github.com/Navteca/jupyterlab-bxplorer/pulls): This would be awesome. We suggest to open an issue or comment an issue before creating the Pull Request.

The extension uses a modified version of the [Chonky File Browser](https://chonky.io/) as its main component. You can find the modified version [here](https://github.com/Navteca/chonky-filebrowser).

We are working on a contributor document and guidelines while refactoring our code to make it more consistent.

<br/>

### Found an issue? Have suggestions?

Please open an [issue](https://github.com/Navteca/jupyterlab-bxplorer/issues), we would like yo hear from you.

<br/>

### Licensing

[BSD 3-Clause License](LICENSE)

<br/>

### Notes for your consideration

- This project is in early stage. We are continously working on it to make it better.
- Chonky is the main component of the extension and we are going to continue modifying it to get it to fit better in this project.
- This is the first extension we put out there. We are aware we have so much to learn from the FLOSS communities and that is one of the reasons we why decided to publish it.
