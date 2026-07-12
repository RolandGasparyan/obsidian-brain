---
name: system-verification-docs
description: Workflow for creating comprehensive, production-ready system verification documentation. Use when tasked with creating technical specifications, implementation guides, testing protocols, or verification checklists for complex software systems.
---

# System Verification Documentation Workflow

This skill provides a structured workflow for generating comprehensive, production-ready documentation packages for complex systems. It ensures all technical requirements are translated into verifiable, step-by-step procedures.

## Core Principles

1. **Verifiability:** Every technical requirement must have a corresponding verification checkpoint.
2. **Structure:** Documentation must be organized into logical phases (e.g., Infrastructure, Data, Logic, UI).
3. **Clarity:** Avoid excessive bullet points; use paragraphs for explanation and tables for structured data (like checklists or test scenarios).
4. **Completeness:** A full package includes specifications, implementation guides, testing protocols, and a master checklist.

## Workflow Steps

When asked to create verification documentation for a system, follow these steps:

### Step 1: Analyze Technical Requirements
Review the system architecture, constraints, and operational rules. Identify the core components that require validation.

### Step 2: Draft the Technical Specification
Create the foundational document (`system_spec.md`) that defines the architecture, logic, constraints, and security requirements. Use this as the source of truth for subsequent documents.

### Step 3: Create the Implementation & Verification Guide
Write a step-by-step guide (`implementation_guide.md`) breaking the deployment into phases. For each step, include explicit verification checkpoints with expected results formatted as tables.

### Step 4: Develop the Testing & Validation Protocol
Create rigorous testing procedures (`testing_protocol.md`) detailing how to validate each component (e.g., load testing, constraint validation, failure recovery).

### Step 5: Generate the Master Verification Checklist
Compile all checkpoints into a single master checklist (`verification_checklist.md`). Organize by category and include columns for Status, Verified By, and Date, plus a formal sign-off section.

### Step 6: Create the Deliverables Index
Generate an index document (`DELIVERABLES_INDEX.md`) summarizing the package contents, key technical requirements, implementation timeline, and document usage guide.

## Best Practices for Document Generation

- **Use Tables:** Present checklists, test scenarios, and parameters in Markdown tables for readability.
- **Maintain Consistency:** Ensure terminology and constraints match exactly across all documents in the package.
- **Progressive Detail:** Start with high-level architecture in the spec, move to step-by-step instructions in the guide, and finish with granular test cases in the protocol.

## Bundled Resources

See the `templates/` directory for structural templates of the required documents.
