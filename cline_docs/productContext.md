# Product Context

## Purpose
GRAAL (GESTION ET RÉPARTITION AUTOMATISÉE DES AMENDEMENTS LÉGISLATIFS) is a tool designed to automate and streamline the processing of legislative amendments. It aims to reduce the workload on agents who are responsible for handling these amendments.

## Problems Solved
1. **Manual Amendment Processing**: Reduces the time-consuming task of manually processing large volumes of legislative amendments
2. **Inconsistent Handling**: Ensures consistent processing through automated grouping and attribution
3. **Historical Context**: Helps maintain consistency by finding similarities with previously processed amendments
4. **Workload Distribution**: Automates the assignment of amendments to appropriate agents
5. **Information Overload**: Provides summaries of amendments for quick understanding

## Core Functionality
The system processes amendments through several key stages:
1. **Grouping**: Identifies and groups similar amendments
2. **Attribution**: Assigns amendments to appropriate agents based on configuration
3. **Opinion Generation**: Provides default opinions for amendments
4. **Similarity Analysis**: Links amendments to historically similar ones
5. **Summarization**: Generates concise summaries using LLM technology
6. **Inadmissible Amendment Handling**: Special processing for inadmissible amendments

## Expected Behavior
- Process amendments without overwriting existing work in Signale
- Maintain data integrity when agents have already started working
- Support multiple project types (PLFSS, PLACSS, etc.)
- Integrate with LLM services (Albert API, Ollama) for intelligent processing
- Preserve existing values when reprocessing amendments
- Handle empty amendment bodies with placeholder text
