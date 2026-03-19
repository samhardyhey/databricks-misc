# Databricks / MLOps practice digest (Marvelous MLOps source)

Auto-generated from `sources/medium/content/articles/*.json`. Use alongside originals on Medium; promote stable guidance into repo docs and Cursor rules.

**Generated:** 2026-03-19 22:08 UTC

## Databricks-focused (tag/title/text match)

### Lecture 10: Implementing Model Monitoring in Databricks

- **URL:** https://medium.com/marvelous-mlops/lecture-10-implementing-model-monitoring-in-databricks-fd560c26805e?source=rss----c122ae9c4ff9---4
- **Author:** Başak Tuğçe Eskili
- **Published:** Wed, 06 Aug 2025 16:55:01 GMT
- **Reading time:** 6 min read
- **Tags:** mlops, data-drift, databricks, model-drift, monitoring

**Extracted list items (candidate tips):**

- Inference Logging: Capturing model inputs and outputs
- Monitoring Table Creation: Transforming raw logs into a format suitable for monitoring
- Scheduled Refreshes: Keeping monitoring data up-to-date
- Monitoring Dashboard: Visualizing metrics and detecting drift
- Runs weekly on Mondays at 6:00 AM Amsterdam time
- Executes the scipts / refresh_monitor.py script with appropriate parameters
- Parses command-line arguments for the root path and environment
- Loads the appropriate configuration
- Calls the monitoring refresh function
- Captures inference data from model serving endpoints
- Transforms this data into a monitoring-friendly format
- Schedules regular updates to keep monitoring current
- Uses Databricks’ built-in quality monitoring features

**Summary excerpt:**

Databricks recently introduced Free Edition, which opened the door for us to create a free hands-on course on MLOps with Databricks.

This article is part of that course series, where we walk through the tools, patterns, and best practices for building and deploying machine learning workflows on Databricks.

Watch the lecture on YouTube.

In the previous lecture , we covered the theory behind ML model monitoring and the tools Databricks provides for it. In this session, we’ll walk through a practical example, from inference tables to Lakehouse Monitoring implementation.

Our monitoring system consists of four key components:

Let’s examine each component in detail.

1. Inference Data Collection

!Make sure that inference tables is enabled for your serving endpoint.

First, we need to collect data from our model serving endpoint. The notebook lecture10.marvel_create_monitoring_table.py demonstrates how to send requests to our endpoint and then process the logged data. In lecture 6 , we learned how to call the model endpoint. There are two ways to do this: either via HTTPS or by using the Workspace Client.

We sample records from our test set and send them to the endpoint to generate some logs.

2. Monitoring Implementation

2.1 Creating and Refreshing Monitoring

---

### Lecture 9: Introduction to Monitoring

- **URL:** https://medium.com/marvelous-mlops/lecture-9-introduction-to-monitoring-8f406aa98160?source=rss----c122ae9c4ff9---4
- **Author:** Başak Tuğçe Eskili
- **Published:** Tue, 05 Aug 2025 21:49:14 GMT
- **Reading time:** 6 min read
- **Tags:** mlops, machine-learning, databricks

**Extracted list items (candidate tips):**

- Stores summary stats for each feature in each time window (count, nulls, mean, stddev, min/max, etc.).
- For inference logs: also tracks accuracy, confusion matrix, F1, MSE, R², and fairness metrics.
- Supports slicing/grouping (e.g., by model ID or feature value).
- Tracks how your data’s column distributions evolve over time using advanced drift detection techniques
- Essential for identifying data quality issues, detecting shifts in real-world behavior, and ensuring that model predictions remain reliable and unbiased.
- Monitoring quality
- Debugging
- Training corpus generation
- Update generate a metrics table
- Automatically update the dashboard
- ML monitoring goes beyond system metrics, it includes data quality, drift, and model performance.
- Databricks Lakehouse Monitoring provides built-in tools for tracking data and model health over time.
- Not all data drift is bad — always check model performance before reacting.
- Inference tables + monitoring pipelines enable end-to-end visibility and alerting in production.

**Summary excerpt:**

Databricks recently introduced Free Edition, which opened the door for us to create a free hands-on course on MLOps with Databricks.

This article is part of that course series, where we walk through the tools, patterns, and best practices for building and deploying machine learning workflows on Databricks.

In this lecture, we’ll dive into one of the most critical (and often misunderstood) aspects of production ML: monitoring.

Watch the lecture on Youtube.

In a ML system, you need to monitor metrics that go beyond the ones you’d expect in any production system (such as system health, errors, and latency, KPIs and infrastructure costs).

In classic software, if code, data, and environment stay the same, so does behavior. ML systems are different: model performance can degrade even if nothing changes in your code or infra because ML is driven by the statistical properties of your data. User behavior can shift, seasonality or upstream data can change.

All can cause your model to underperform, even if everything else is “the same.” That’s why MLOps monitoring includes data drift, model drift, and statistical health, not just system metrics.

Data Drift: It happens when the distribution of the input data shifts over time, even if the relationship between inputs and outputs stays the same. For example, let’s say there is a lot of new houses entering the market in a certain district. People’s preferences, the relationship between features and price stays the same. But because the model hasn’t seen enough examples of new houses, its performance drops, not because the logic changed, but because the data shifted. In this case, data drift is the root cause of model degradation.

Concept Drift: It happens when the relationship between input features and the target variable changes over time so model’s original assumptions about how inputs relate to outputs no longer holds. Let’s look at housing prices example: new houses enter the market, and the government introduces a subsidy for families with children which leads to larger houses sold for lower prices. This is a shift in the underlying relationship between features like house size and the final price. Even if the input data distribution doesn’t change much, the model’s predictions will become less accurate

Not all drift is bad! Sometimes, your model is robust to input changes, and performance remains stable. Check this article for a real example. Suppose you detect significant data drift in the “temperature” f…

---

### Lecture 8: CI/CD & Deployment Strategies

- **URL:** https://medium.com/marvelous-mlops/lecture-8-ci-cd-deployment-strategies-71dbdd455299?source=rss----c122ae9c4ff9---4
- **Author:** Başak Tuğçe Eskili
- **Published:** Mon, 04 Aug 2025 19:09:41 GMT
- **Reading time:** 8 min read
- **Tags:** mlops, databricks, machine-learning

**Extracted list items (candidate tips):**

- Catalogs (e.g., mlops_dev, mlops_acc, mlops_prd)
- Schemas within catalogs (in our case, we have the same schema name in each catalog, marvel_characters)
- Assets within schemas (tables, views, models, etc.)
- All ML pipelines form all workspaces (dev, acc, prd) have read access to production data (e.g., prd_gold), ensuring consistency.
- From each workspace, the data can only be wtitten to its own catalog.
- Users only have direct access to the dev workspace; deployments to acc/prd must go through CI/CD pipelines, using service principals for security and traceability.
- Feature branches are created from main.
- Developers open PRs to main, triggering the CI pipeline.
- CI runs pre-commit checks, unit tests, and version checks.
- At least 2 approvals are required to merge (enforced via branch protection rules).
- Direct pushes to main are not allowed.
- Runs on PRs and pushes to main/dev
- Installs dependencies, runs linting and tests
- Checks that the version is unique (to prevent accidental duplicate releases)
- Only runs on push to main
- Builds the wheel (databricks bundle deploy takes care of that)
- Deploys the Lakeflow job to both acceptance and production using environment-specific secrets
- Uses the Databricks CLI to deploy bundles
- Security: SPNs are not tied to any individual, so if someone leaves the team, you don’t risk losing access or exposing credentials.
- Least privilege: SPNs can be granted only the permissions they need for deployment — nothing more.
- Auditability: All actions performed by the CI/CD pipeline are clearly attributable to the SPN, making it easy to track changes and meet compliance requirements.
- Automation: SPNs enable fully automated, hands-off deployments, since their credentials (client ID and secret) can be securely stored in your CI/CD system (like GitHub Actions).
- Create a Service Principal in Databricks:
- Go to the Databricks workspace admin console.
- Navigate to User Management → Service Principals.
- Click Add Service Principal and follow the prompts.
- Note the Client ID and Client Secret that are generated.
- Grant the SPN the necessary privileges in Unity Catalog, jobs, and workspace resources (e.g., CAN_MANAGE or CAN_RUN on the relevant schemas, jobs, and endpoints).
- Make sure the SPN has access only to the environments it should deploy to (e.g., acc and prd).
- DATABRICKS_CLIENT_ID (the SPN’s client ID)
- DATABRICKS_CLIENT_SECRET (the SPN’s client secret)
- DATABRICKS_HOST (your Databricks workspace URL)
- Navigate to your endpoint in the Databricks UI
- Click on “Permissions”
- Add your Service Principal with “Can Query” permission
- Catalogs, schemas, and workspaces provide clean separation and access control.
- Service principals ensure automation is secure and scoped.
- Git flow and branch protection rules enforce code quality and review.
- CI/CD pipelines automate validation and deployment, with no manual pushes to production.

**Summary excerpt:**

Databricks recently introduced Free Edition , which opened the door for us to create a free hands-on course on MLOps with Databricks.

This article is part of that course series, where we walk through the tools, patterns, and best practices for building and deploying machine learning workflows on Databricks.

In this lecture, we’ll explore how to structure your data and assets for robust, secure, and scalable machine learning operations on Databricks, and how to automate deployments using CI/CD pipelines.

Watch the lecture on YouTube .

Unity Catalog, Workspaces, and Data Organization

We’ve already interacted with Unity Catalog, using it to create delta tables and register models. For a workspace to use Unity Catalog, it must be attached to a Unity Catalog metastore, which is the top-level container for all data and AI asset metadata.

You can only have one metastore per cloud region, and each workspace can only be attached to one metastore in that region.

Unity Catalog organizes assets in a three-tier hierarchy:

Assets are referenced using a three-part naming convention: catalog.schema.asset.

Access Control: Securables and Permissions

In Databricks, permissions can be set on the workspace and on Unity Catalog level.

Workspace-level securables: Notebooks, clusters, jobs — accessed via ACLs.

---

### Lecture 7: Databricks Asset Bundles

- **URL:** https://medium.com/marvelous-mlops/lecture-7-databricks-asset-bundles-c6cef7b48017?source=rss----c122ae9c4ff9---4
- **Author:** Başak Tuğçe Eskili
- **Published:** Sun, 03 Aug 2025 14:49:48 GMT
- **Reading time:** 7 min read
- **Tags:** databricks-asset-bundles, mlops, databricks

**Extracted list items (candidate tips):**

- Terraform: Full infrastructure-as-code control, but can be complex.
- Databricks APIs: Flexible, but requires custom scripting.
- Databricks Asset Bundles (DAB): The recommended, declarative, YAML-based approach.
- Declarative YAML configuration: Define everything in one place.
- Multi-environment support: Easily target dev, staging, prod, etc.
- CI/CD friendly: Fits naturally into automated pipelines.
- Version-controlled: All changes are tracked in your repo.
- Preprocessing. Runs a data processing script scripts/process_data.py .
- Train & Evaluate. Trains and evaluates the model using scripts/train_register_custom_model.py .
- Model Update. Conditional step: if the new model is better, release a flag and register it.
- Deployment. Deploy the registered model by creating or updating a serving endpoint using scripts/deploy_model.py .
- databricks bundle validate — validate your bundle
- databricks bundle deploy — deploys your bundle
- databricks bundle run — run the job
- databricks bundle destroy — Tear down resources

**Summary excerpt:**

Databricks recently introduced Free Edition , which opened the door for us to create a free hands-on course on MLOps with Databricks.

This article is part of that course series, where we walk through the tools, patterns, and best practices for building and deploying machine learning workflows on Databricks.

In this lecture, we’ll focus on how to automate and the entire ML workflow using DAB. You can also follow along the lecture with the full walkthrough on the Marvelous MLOps YouTube channel:

All code covered in this repository is available here .

Why Databricks Asset Bundles?

When deploying resources and their dependencies on Databricks, you have a few options:

DAB offers a balance between simplicity and power. Under the hood, it leverages Terraform, so you get all the benefits of infrastructure-as-code, without having to manage raw Terraform code yourself. This is ideal for teams looking to standardize and automate job deployments in a scalable, maintainable way.

What is DAB?

Databricks Asset Bundle (DAB) is the way to package your code, jobs, configuration, and dependencies together in a structured, version-controlled format. With DAB, you define jobs, notebooks, models, and their dependencies using YAML files.

Key features:

What is a Lekeflow job?

Lakeflow Jobs (previously Databricks workflows) provide the execution and orchestration layer. Workflows let you run tasks (notebooks, scripts, SQL) on a schedule or in response to events, with support for dependencies, retries, parameter passing, and alerts.

---

### Lecture 6: Deploying a model serving endpoint

- **URL:** https://medium.com/marvelous-mlops/deploying-a-model-serving-endpoint-957d6d828739?source=rss----c122ae9c4ff9---4
- **Author:** Vechtomova Maria
- **Published:** Sat, 02 Aug 2025 12:21:50 GMT
- **Reading time:** 6 min read
- **Tags:** machine-learning, mlops, databricks

**Extracted list items (candidate tips):**

- Effortless deployment of registered MLflow models
- Automatic scaling, including scale-to-zero when there’s no traffic
- Built-in monitoring in the Databricks UI (track latency, throughput, error rates)
- Seamless integration with models registered in Unity Catalog
- No control over runtime environment: Databricks chooses the environment for you, which can be a constraint if you need specific library versions.
- No control over cluster size. Each replica is limited to 4 GB RAM (CPU), which may not be enough for very large models.
- Workload size options: You can choose the workload size (Small, Medium, Large, XL, etc.), which determines the number of compute units per replica. For demanding use cases, you can scale up to 512 units per endpoint on request.

**Summary excerpt:**

Databricks recently introduced Free Edition, which opened the door for us to create a free hands-on course on MLOps with Databricks .

This article is part of that course series, where we walk through the tools, patterns, and best practices for building and deploying machine learning workflows on Databricks.

This is lecture 6 (out of 10). Let’s dive into deploying model serving endpoints and implementing A/B testing on Databricks. You can also follow along with the full walkthrough on the Marvelous MLOps YouTube channel.

In previous lectures, you learned how to train, log, and register models with MLflow. Now, it’s time to expose those models behind an API using Databricks Model Serving.

Databricks Model Serving is a fully managed, serverless solution that allows you to deploy MLflow models as RESTful APIs without the need to set up or manage any infrastructure.

Model serving limitations

Databricks model serving makes the transition from experimentation to production incredibly smooth. It’s ideal for teams who want to focus on building great models, not managing infrastructure. However, if you choose to deploy a model serving endpoint on Databricks, you must be aware of its limitations, such as:

The workload size determines the number of compute units available, with each unit able to handle one request at a time (4 for Small, 8–16 for Medium, 16–64 for Large). This does not directly translate to queries per second (QPS), as throughput depends on the execution time of the model’s predict function. For example, if prediction takes 20 ms, 4 compute units can handle approximately 4 / 0.02 = 200 QPS.

Autoscaling is based on the number of required units, not CPU or RAM usage. The number of required units is calculated as:

Example: 1,000 QPS × 0.02s = 20 units needed.

Payload structure

Another serving limitation is the payload structure. Databricks uses MLflow serving behind the scenes, and the payload is defined by it. You have some ability to adapt the payload for your needs by using pyfunc, but you have no influence on the global payload structure.

---

### Lecture 5: Model serving architectures

- **URL:** https://medium.com/marvelous-mlops/model-serving-architectures-b2f2c11cb4d7?source=rss----c122ae9c4ff9---4
- **Author:** Vechtomova Maria
- **Published:** Fri, 01 Aug 2025 17:36:37 GMT
- **Reading time:** 4 min read
- **Tags:** machine-learning, mlops, databricks

**Extracted list items (candidate tips):**

- serving batch predictions (feature serving)
- model serving
- model serving with feature lookup

**Summary excerpt:**

Databricks recently introduced Free Edition , which opened the door for us to create a free hands-on course on MLOps with Databricks .

This article is part of the course series, where we walk through the tools, patterns, and best practices for building and deploying machine learning workflows on Databricks.

This is lecture 5 where we walk about model serving architectures on Databricks. View the lecture on Marvelous MLOps YouTube channel.

Model serving is a challenging topic for many machine learning teams. In an ideal scenario, the same team that develops a model, should be responsible for model deployment. However, this is not always feasible due to the knowledge gap or organizational structure. In that scenario, once model is ready, it is handed over to another team for deployment. It creates a lot of overhead when it comes to debugging and communication.

That’s where Databricks model serving can help a lot. Databricks model and feature serving use serverless, which simplifies the infrastructure side of the deployment, and a model endpoint can be created with one Python command (using Databricks sdk). It allows data science teams to own the deployment end-to-end and minimize the dependence on other teams.

In this article, we’ll discuss the following architectures:

Feature serving

Serving batch predictions is probably one of the most popular and underestimated types of machine learning model deployment. Predictions are computed in advance using a batch process, stored in an SQL or in-memory database, and retrieved at request.

This architecture is very popular in the case of personal recommendation with low latency requirements. For example, an e-commerce store may recommend products to customers on various pages of the website.

Databricks Feature Serving is a perfect fit here. A scheduled Lakeflow job preprocesses data, retrains the model, and writes predictions to a feature table in Unity Catalog . These features are synced to an Online Store and exposed through a Feature Serving endpoint , defined by a FeatureSpec, a blueprint that combines feature functions (how features are calculated) with feature lookups (how they’re retrieved). Your application can then query this endpoint in real time to get fresh features for inference.

Model serving

Model serving assumes that model is deployed behind and endpoint, and all features are available through the payload. This is not the most realistic scenario, but can be still used in certain use cases, w…

---

### Lecture 4: Logging and registering models with MLflow

- **URL:** https://medium.com/marvelous-mlops/logging-and-registering-models-with-mlflow-b9446a9d91cf?source=rss----c122ae9c4ff9---4
- **Author:** Vechtomova Maria
- **Published:** Thu, 31 Jul 2025 18:51:17 GMT
- **Reading time:** 10 min read
- **Tags:** databricks, mlops, machine-learning

**Extracted list items (candidate tips):**

- Signature is inferred using model input (X_train) and model output (the result of running the predict function on the pipeline), and passed when logging the model. If the signature is not provided, we would not be able to register model in Unity Catalog later.
- Input datasets (train and test sets, including the delta table version) are logged under the MLflow run to ensure that we can get the exact version of data used for training and evaluation, even if data was modified later, thanks to the time travel functionality of delta tables. Remember to set a proper retention period on the delta table (default is 7 days), otherwise you may not be able to access the exact version of the table if VACUUM command was executed. Most accounts have predictive optimization enabled by default, which means that Databricks automatically executes it as part of the optimization process.

**Summary excerpt:**

Databricks recently introduced Free Edition , which opened the door for us to create a free hands-on course on MLOps with Databricks .

This article is part of the course series, where we walk through the tools, patterns, and best practices for building and deploying machine learning workflows on Databricks

Let’s dive into lecture 4. View the lecture on Marvelous MLOps YouTube channel.

In the previous lecture , we have logged metrics, parameters, various artifacts, but have not logged a model yet. You could just saved a model in a .pkl file, but MLflow goes beyond that: it provides a standardized format called an MLflow Model, which defines how a model, its dependencies, and its code are stored. This is essential for downstream tasks like real-time serving, which will be covered later in the course.

A model can be logged using the mlflow.<model_flavor>.log_model() function. MLflow supports a wide range of flavors, such as lightgbm, prophet, pytorch, sklearn, xgboost, and many more. It also supports any custom model logics through PythonModel base class , which can be logged using pyfunc flavor.

Basic model: log, train, and register

To demonstrate logging, we’ll start with training a scikit-learn pipeline (referred to as Basic model) and logging it using sklearn flavor. We’ll walk through the notebooks/lecture4.train_register_basic_model.py code from the course GitHub repo .

Since we are interacting with MLflow, we need to set up tracking and registry URIs just as we did in lecture 3 :

Then we’ll load the project configuration, initialize the SparkSession, and define tags we’ll need to tag the MLflow run and registered model:

We’ll need those to initialize an instance of BasicModel class. Then we load the data, prepare features, train and log the model:

Let’s go through the logics behind the BasicModel class to understand what’s going on. After the class gets initialized, we set certain class attributes such as features, target, parameters, and model name.

We load the train and the test set using pyspark, and we’ll need these pyspark dataframes later to log the model input, together with the delta table version we retrieve. We also use toPandas() command to create pandas dataframes which are used for model training and evaluation.

---

### Lecture 3: Getting started with MLflow

- **URL:** https://medium.com/marvelous-mlops/getting-started-with-mlflow-0350a6b7ff33?source=rss----c122ae9c4ff9---4
- **Author:** Vechtomova Maria
- **Published:** Wed, 30 Jul 2025 13:43:23 GMT
- **Reading time:** 6 min read
- **Tags:** databricks, mlops, machine-learning

**Extracted list items (candidate tips):**

- The tracking and the registry URI must contain the profile that you used to log in (which is defined in the .databrickscfg file, for exampledbc-1234a567-b8c9).
- We want multiple developers with a different profile name to collaborate on the same code base.
- We only want to set the tracking and the registry URI when running code outside of Databricks.

**Summary excerpt:**

Databricks recently introduced Free Edition , which opened the door for us to create a free hands-on course on MLOps with Databricks .

This article is part of that course series, where we walk through the tools, patterns, and best practices for building and deploying machine learning workflows on Databricks.

Let’s dive into lecture 3. View the lecture on Marvelous MLOps YouTube channel.

MLflow is probably the most popular tool for model registry and experiment tracking out there. MLFlow is open source and integrates with a lot of platforms and tools.

Due to its extensive support and a lot of options, getting started with MLflow may feel overwhelming. In this lecture, we will get back to the basics, and will review 2 most important classes in MLFlow that form the foundation of everything else , mlflow.entities.Experiment and mlflow.entities.Run.

We will see how those entities get created, how you can retrieve them, and how they change based on different input parameters. In this course, the Databricks version of MLflow is used, so it contains some Databricks-specific information. However, the idea is generalizable to any MLflow instance.

Before we go any further, let’s discuss how we can authenticate towards MLflow tracking server on Databricks.

Tracking URI

By default, MLflow will track experiment runs using the local file systems, and all the metadata will be stored in the ./mlruns directory. We can verify that by retrieving the current tracking URI:

In lecture 2 , we explained how we can authenticate towards Databricks using Databricks CLI, which we continued to use when developing in VS Code. Now we must make MLflow aware of it, and use Databricks MLflow tracking server.

This can be done by calling mlflow.set_tracking_uri().Even though we’re only using experiment tracking for now, starting with MLflow 3, it’s also necessary to set the registry URI using mlflow.set_registry_uri(). There are a couple of things to pay attention to:

This leads us to the following possible solution. We can then define whether the code runs within a Databricks environment by checking that the DATABRICKS_RUNTIME_VERSION environment variable is available. Every developer can store the profile name in .env file (which is ignored by git via .gitignore file), and set environment variable PROFILE using Python package dotenv:

---

## Other Marvelous MLOps articles

### UV All the Way: Your Go-To Python Environment Manager

- **URL:** https://medium.com/marvelous-mlops/uv-all-the-way-your-go-to-python-environment-manager-95ed59afa373?source=rss----c122ae9c4ff9---4
- **Author:** Boldizsar Palotas
- **Published:** Mon, 10 Nov 2025 07:27:21 GMT
- **Reading time:** 7 min read
- **Tags:** uv, python

**Extracted list items (candidate tips):**

- On MacOS, make sure you have Homebrew installed , then run brew install uv to install uv.
- On Linux, run curl -LsSf https://astral.sh/uv/install.sh | sh to install uv.
- On Windows, run powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex" to install uv.
- (Otherwise consult the uv installation docs ).
- It created a .git folder and added a standard .gitignore file to help track your project in Git.
- It created a pyproject.toml which is the standard (not uv-specific!) config file for Python projects.
- It created a main.py which is just a dummy file to get you started. We'll edit this later.
- It created a .python-version file which tells uv which version of Python to use.
- It created an empty README.md which you could also use to take notes during this tutorial.
- A uv.lock file has been generated which locks (in other word: pins) all dependencies to a current version.
- A .venv folder has been created and it now contains a valid Python virtual environment. (It's very similar to a venv you would have created with python3 -m venv .venv.)
- Inside the alice-python folder, create a subfolder named alice (or your name, but make it lowecase only, keeping it a valid Python module or variable name).
- Then move main.py inside the new alice folder.

**Summary excerpt:**

In 2025 the best way to manage Python projects is using uv . This tutorial helps you set up a modern Python project from scratch using uv.

The two most important things that uv manages for you is a project-specific virtual environment (venv), and all the project dependencies in that venv.

Let’s start creating stuff!

Install uv

If you haven’t already, install uv on your machine. Open a shell or terminal to run these commands:

Make sure you have uv installed and available as a command line application. You should be able to open a new shell and run the following command:

By the time you read this, uv will be updated many times, so you should expect to see a newer version.

Create a project with uv

Let’s create a personal Python project for you using uv.

In this example we’ll pretend you’re caled “Alice” and use that as an example. Feel free to sub Alice with your own name or whatever name you want to use for this project.

Let’s open the shell again, and create a project folder. After that let’s change into that folder and run all further commands inside that folder.

(On Windows use Powershell, and you can omit the -p flag to mkdir.)

---

### Patterns and Anti-Patterns for Building with LLMs

- **URL:** https://medium.com/marvelous-mlops/patterns-and-anti-patterns-for-building-with-llms-42ea9c2ddc90?source=rss----c122ae9c4ff9---4
- **Author:** hugo bowne-anderson
- **Published:** Mon, 27 Oct 2025 10:24:02 GMT
- **Reading time:** 6 min read
- **Tags:** ai, machine-learning, genai, data-science

**Extracted list items (candidate tips):**

- Spotify
- Apple
- Full notes and more episodes
- Reframe the problem. The goal is not to replace human judgment but to save users time.
- Design systems that make the AI’s work transparent, allowing users to verify the output and act as the final authority.
- By setting the correct expectation, that the AI is a time-saving assistant, not an infallible oracle, you can deliver value without overpromising on reliability [ 00:04:30 ].
- Keep the user in the loop. Break down large tasks into smaller steps and build in opportunities for the agent to ask clarifying questions.
- Make the agent’s process and intermediate steps visible to the user.
- This collaborative approach narrows the solution space and ensures the final output aligns with the user’s actual intent [ 00:09:10 ].
- Practice responsible “context engineering.”
- Instead of brute-forcing the context window, first lay out all potential information sources.
- Then, create a relevance-ranking algorithm to tier the context, ensuring only the most vital information makes it into the prompt.
- Build a template that fits within a sensible token budget, not the maximum window size, ensuring the final context is lean, readable, and effective [ 00:13:20 ].
- Start with the simplest viable solution.
- Build a single-prompt, single-model system first to understand its failure modes and limitations.
- Only when the pain of the simple approach becomes clear should you incrementally add complexity.
- This process ensures that if a multi-agent system is truly needed, its design is informed by real-world constraints rather than assumptions [ 00:19:15 ].
- Build your own RAG system, and consider the individual pieces of the pipeline: indexing, query creation, retrieval, and generation.
- By isolating these components, you can debug them independently.
- If the generated answer is wrong, you can inspect the retrieved context to see if the issue is poor retrieval.
- If the context is good but the answer is bad, the problem lies with the generation prompt or model.
- This separation is key to building a reliable and maintainable system [ 00:22:10 ].
- Break the problem into smaller, atomic pieces.
- Instead of one large prompt asking for everything, use several smaller, focused prompts, which can even be run in parallel.
- For example, rather than asking a model to “find all hallucinations,” iterate through each fact and ask, “Is this statement supported by the source? True or False.”
- This trades a small amount of latency for a large gain in accuracy and reliability [ 00:28:10 ].
- Dig in and build essential components yourself, at least initially. Understand that at its core, an LLM call is just an HTTP request.
- For domain-specific needs like evaluation or human review, a simple, custom-built tool is often more effective than a generic platform.
- Adopt frameworks mindfully, pick one that solves a clear problem, and anticipate that you will still need to write and rewrite code as your needs evolve [ 00:31:10 ].
- Accuracy: Reframe the goal. Instead of trying to make AI 100% accurate, make it a way to augment your users and save them time.
- Oversight: When working with complex workflows, keep the user in the loop and break down large agentic tasks into smaller, supervised steps.
- Context: Avoid model distraction by selectively curating context. Rank context by relevance and select only the most relevant information.
- Complexity: Start with the simplest possible solution before adding multi-agent complexity.
- RAG: In order to facilitate easy debugging, design RAG as a transparent pipeline of indexing, query generation, retrieval, and generation.
- Prompts: Improve accuracy by decomposing complex multi-part prompts into several prompts that are easier for the model to process.
- Frameworks: Build core components yourself and adopt third-party tools mindfully, anticipating change.

**Summary excerpt:**

Seven Deadly Sins of AI App Development

A bit about our guest author: Hugo Bowne- Anderson advises and teaches teams building LLM-powered systems, including engineers from Netflix, Meta, and the United Nations through my course on the AI software development lifecycle . It covers everything from retrieval and evaluation to agent design and all the steps in between. Use the code MARVELOUS25 for 25% off.

In a recent Vanishing Gradients podcast, I sat down with John Berryman, an early engineer on GitHub Copilot and author of Prompt Engineering for LLMs .

We framed a practical discussion around the “Seven Deadly Sins of AI App Development,” identifying common failure modes that derail projects.

For each sin, we offer a “penance”: a clear antidote for building more robust and reliable AI systems.

You can also listen to this as a podcast:

👉 This was a guest Q&A from our July cohort of Building AI Applications for Data Scientists and Software Engineers. Enrolment is open for our next cohort (starting November 3) . 👈

Sin 1: Demanding 100% Accuracy

The first sin is building an AI product with the expectation that it must be 100% accurate, especially in high-stakes domains like legal or medical documentation [ 00:03:15 ]. This mindset treats a probabilistic system like deterministic software, a mismatch that leads to unworkable project requirements and potential liability issues.

The Solution/Penance:

Sin 2: Granting Agents Too Much Autonomy

This sin involves giving an agent a large, complex, closed-form task and expecting a perfect result without supervision [ 00:07:20 ]. Due to the ambiguity of language and current model limitations, the agent will likely deliver something that technically satisfies the request but violates the user’s implicit assumptions. This is particularly ineffective for tasks with a specific required solution, though it can be useful for open-ended research.

---
