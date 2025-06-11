# LLMail-Inject: Adaptive Prompt Injection Challenge

<p align="center">
<img src="/assets/overview.png" width="100%" alt="Competition Overview Image">
</p>

## Re:LLMail-Inject
We are running a follow-up phase of this challenge with improved defenses! Please check the "Scenarios" and "Rules" tabs for details.

## Competition Overview

The goal of this challenge is to evade prompt injection defenses in a simulated LLM-integrated email client, the LLMail service. The LLMail service includes an assistant that can answer questions based on the users’ emails and perform actions on behalf of the user, such as sending emails. Since this assistant makes use of an instruction-tuned large language model (LLM), it naturally includes several defenses against indirect prompt injection attacks.

In this challenge, participants take the role of an attacker who can send an email to the (victim) user. The attacker’s goal is to cause the user’s LLM to perform a specific action, which the user has not requested. In order to achieve this, the attacker must craft their email in such a way that it will be retrieved by the LLM and will bypass the relevant prompt injection defenses. This challenge assumes that the defenses are known to the attacker, and thus requires the attacker to create adaptive prompt injection attacks.

## Quick Start

To participate, you will need to sign into this website, using a GitHub account, and create a team (ranging from 1 to 5 members). Entries can be submitted directly via this website or programmatically via an API.

## System Design and Workflow

This section describes how the different entities interact with simulated LLMail service.

- **Attacker (challenge participant).** The attacker can send one email to the user (step 1 in the figure above). The attacker’s goal is to cause the LLMail service to execute a command that the user did not intend. The attacker has full control over the text in their email.

- **User.** The user interacts with the LLMail service to read e-mails, ask questions, summarize e-mails, etc. (step 2 in the figure).

- **Email database.** There is a database containing several simulated emails, as well as the attacker’s email. The LLMail service includes a retriever component that searches this database and retrieves specific emails, depending on the scenario (step 3 in the figure).

- **LLM.** The LLMail service uses an LLM to process the user’s requests and generate responses based on the retrieved emails (step 4 in the figure). The LLM can also generate an api_call to send an email on behalf of the user. The attacker cannot observe the output of the LLM.

- **Defenses.** The LLMail service is equipped with several prompt injection defenses that run whenever the LLM is used (step 5 in the figure). In addition, the name of the API for sending an email (i.e., the attacker’s goal) is not disclosed to the attacker and the LLMail system will filter out the API name from any received emails.

## Contact

<p>
  If you need to get in touch with the organizers, please send an email to 
  <a href="mailto:llmailinject@microsoft.com" class="email-link">llmailinject@microsoft.com</a>.
</p>

## Competition Organizers

The competition is jointly organized by the following people from Microsoft (1), ISTA (2), and ETH Zurich (3):

Aideen Fay\*<sup>1</sup>, Sahar Abdelnabi\*<sup>1</sup>, Benjamin Pannell\*<sup>1</sup>, Giovanni Cherubin\*<sup>1</sup>, Ahmed Salem<sup>1</sup>, Andrew Paverd<sup>1</sup>, Conor Mac Amhlaoibh<sup>1</sup>, Joshua Rakita<sup>1</sup>, Santiago Zanella-Beguelin<sup>1</sup>, Egor Zverev<sup>2</sup>, Mark Russinovich<sup>1</sup>, and Javier Rando<sup>3</sup>

(\*: Core contributors).

<p align="center">
  <img src="/assets/microsoft-logo.png" width="200" alt="Microsoft Logo">
  <img src="/assets/ista-logo.jpg" width="200" alt="ISTA Logo" style="padding-right: 5px;">
  <img src="/assets/ethzurich-logo.jpg" width="200" alt="ETH Zurich Logo" style="padding-left: 30px;">
</p>
