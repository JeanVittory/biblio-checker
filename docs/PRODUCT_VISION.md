# Academic Bibliographic Verification System

---

## Introduction

This project aims to design and develop an **academic bibliographic verification system** focused on detecting **real, incomplete, or fabricated references**, especially in the context of the growing use of **generative artificial intelligence models** in university and academic work.

In recent years, the use of AI tools has facilitated the writing and structuring of academic texts, but it has also introduced a critical problem: the generation of **plausible yet nonexistent bibliographic citations** (*bibliographic deep fakes*). These references may include authors, titles, journals, and years that appear real but do not exist in any reliable academic repository.

This system seeks to **mitigate that risk** by providing a technical layer of automatic validation against **open and verifiable academic sources**, not by prohibiting the use of AI, but by **complementing it with mechanisms for control and evidence**.

---

## 🎯 General Objective

To build a platform that enables:

* Verifying whether a bibliographic reference **actually exists**
* Determining whether it corresponds to a **peer-reviewed article** or a **preprint**
* Detecting **suspicious or fabricated references**
* Providing **traceable evidence** for students, instructors, and reviewers
* Facilitating the **guided correction** of incorrect references

---

## 🧠 System Principles

* **AI is not an academic source**

  The system does not generate citations; it only validates their existence against real sources.

* **Evidence-based verification**

  Each result must be justified with data obtained from open academic APIs.

* **Regional and multilingual coverage**

  Validation prioritizes scientific production from Latin America, including articles without DOI and regional journals.

* **Traceability and auditability**

  Every verification must be reproducible and auditable.

* **Modular and extensible design**

  New sources, rules, and validations can be added without breaking the existing system.

---

## 🔍 Initial Scope

The system focuses on reference verification using the following sources:

* **OpenAlex** → general academic search and validation
* **SciELO (ArticleMeta)** → regional validation (LATAM, ES/PT)
* **arXiv** → scientific preprint verification

In the future, the system may be extended to other sources such as Crossref, PubMed, or other institutional repositories.

---

## 🚀 Long-Term Vision

The long-term vision of the project is to become an **academic trust layer**, integrable with:

* educational platforms (LMS)
* text editors
* academic review systems
* university evaluation workflows

The goal is not to punish the use of AI, but to **ensure academic integrity in an era of automated content generation**.

