# GEMINI.md

## Project Overview

This project, "AI-Sheet," is a smart spreadsheet tool built with Python. It provides a graphical user interface (GUI) to automate and intelligently handle spreadsheet operations, especially complex formula generation and batch data processing tasks.

The application is built using the following technologies:

*   **GUI:** Tkinter
*   **Data Processing:** pandas, openpyxl
*   **LLM Integration:** openai

The project is structured into the following directories:

*   `ui/`: Contains the UI components for each tab in the application.
*   `modules/`: Contains the core business logic for features like formula generation, batch processing, and configuration management.
*   `config/`: Contains configuration files for models and prompts.
*   `units/`: Contains low-level units like the LLM client.
*   `main.py`: The main entry point of the application.

## Building and Running

To run this project, you need to have Python installed. Then, follow these steps:

1.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run the application:**
    ```bash
    python main.py
    ```

Upon first launch, you will need to configure the large language model (LLM) settings in the "⚙️ 配置管理" (Configuration Management) tab.

## Development Conventions

*   **UI and Logic Separation:** The project follows a clear separation between the UI (in the `ui/` directory) and the business logic (in the `modules/` directory).
*   **Configuration-driven:** The application's behavior is driven by configuration files in the `config/` directory. This includes LLM model configurations (`models_config.json`) and prompts (`prompts.json`).
*   **Modular Design:** The application is designed in a modular way, with each feature encapsulated in its own set of UI and logic files.
*   **Error Handling:** The code includes error handling to gracefully manage exceptions and provide informative messages to the user.

## Core Components

*   **`main.py`**: The main entry point of the application. It initializes the Tkinter root window and the main application class `AISheetApp`.
*   **`AISheetApp`**: The main application class that manages the different tabs and the overall application flow.
*   **`ui/`**: This directory contains the UI for each tab in the application. Each tab is a separate class that inherits from `ttk.Frame`.
    *   **`multi_excel_tab.py`**: Handles the UI for uploading and managing multiple Excel files and sheets.
    *   **`formula_generation_tab.py`**: Provides the UI for generating Excel formulas from natural language descriptions.
    *   **`llm_processing_tab.py`**: Implements the UI for batch processing of Excel data using an LLM.
    *   **`python_processing_tab.py`**: Provides a two-stage UI for processing data with Python code generated from natural language, allowing users to analyze requirements and execute the processing strategy.
    *   **`config_tab.py`**: Allows users to configure the LLM models.
    *   **`prompt_management_tab.py`**: Provides a UI for managing the prompts used for formula generation and batch processing.
*   **`modules/`**: This directory contains the backend logic for the application.
    *   **`multi_excel_utils.py`**: Provides utility functions for handling multiple Excel files.
    *   **`formula_generator.py`**: Contains the logic for generating Excel formulas using an LLM.
    *   **`llm_batch_processor.py`**: Implements the logic for batch processing of Excel data using an LLM.
    *   **`python_code_processor.py`**: Orchestrates the Python code processing workflow, from requirement analysis to code generation and execution.
    *   **`python_code_executor.py`**: Safely executes Python code in an isolated environment, managing dependencies and capturing outputs.
    *   **`config_manager.py`**: Manages the LLM model configurations.
    *   **`prompt_manager.py`**: Manages the prompts.

## File Descriptions

*   **`main.py`**: The main entry point of the application.
*   **`requirements.txt`**: A list of the Python dependencies required to run the project.
*   **`README.md`**: The main documentation file for the project.
*   **`config/models_config.json`**: Stores the configurations for the LLM models.
*   **`config/prompts.json`**: Stores the prompts used for formula generation and batch processing.
*   **`ui/multi_excel_tab.py`**: UI for the multi-excel upload and selection tab.
*   **`modules/multi_excel_utils.py`**: Backend logic for handling multiple excel files.
*   **`ui/formula_generation_tab.py`**: UI for the formula generation tab.
*   **`modules/formula_generator.py`**: Backend logic for generating formulas.
*   **`ui/llm_processing_tab.py`**: UI for the LLM batch processing tab.
*   **`modules/llm_batch_processor.py`**: Backend logic for LLM batch processing.
*   **`ui/python_processing_tab.py`**: UI for the Python code processing tab.
*   **`modules/python_code_processor.py`**: Backend logic for analyzing and processing data using generated Python code.
*   **`modules/python_code_executor.py`**: Backend logic for executing Python code in a sandboxed environment.
*   **`ui/config_tab.py`**: UI for the model configuration tab.
*   **`modules/config_manager.py`**: Backend logic for managing model configurations.
*   **`ui/prompt_management_tab.py`**: UI for the prompt management tab.
*   **`modules/prompt_manager.py`**: Backend logic for managing prompts.