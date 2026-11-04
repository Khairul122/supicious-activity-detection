# AI CCTV Suspicious Activity Detection: Commercial License Agreement

**Version 1.0, November 2026**

Copyright © 2026 Khairul (github.com/Khairul122). All rights reserved.

This Commercial License Agreement (the "Agreement") is between **Khairul** (the "Licensor") and the person or legal entity that obtains a license to the Software (the "Licensee"). By downloading, installing, copying, or using the Software, the Licensee agrees to this Agreement. If the Licensee does not agree, the Licensee must not use the Software.

---

## 1. Definitions

1.1 **"Software"** means the AI CCTV Suspicious Activity Detection system: its source code, compiled files, trained model weights (`best.pt`, `motor.pt`), configuration files, database schema, user interface, graphics, logo, documentation, and any update the Licensor provides. It excludes the Third-Party Components.

1.2 **"Third-Party Components"** means software, models, fonts, icons, and data owned by others and listed in `THIRD_PARTY_NOTICES.md`.

1.3 **"Site"** means one physical location of the Licensee, such as one shop, office, warehouse, or parking area, at one street address.

1.4 **"Production Use"** means any use other than evaluation, including monitoring real premises or real people.

1.5 **"Order"** means the purchase confirmation, invoice, or freelance platform order that states the license type, the Licensee's name, the Sites, and the fee.

1.6 **"Client"** means a third party for whom a Developer Licensee installs or operates the Software.

## 2. License types

The license type stated in the Order applies. If the Order states no type, the Single-Site License applies.

| License | Who may use it | Where | Production Use |
| --- | --- | --- | --- |
| **Evaluation** | The Licensee only | Test computers | No. Limited to 30 days from first installation |
| **Single-Site** | One legal entity | One Site, one server, unlimited cameras at that Site | Yes |
| **Multi-Site** | One legal entity and its wholly owned branches | The Sites listed in the Order | Yes |
| **Developer** | An integrator, agency, or freelancer | Installations for Clients approved in writing by the Licensor | Yes, for each approved Client |

## 3. License grant

3.1 Subject to this Agreement and to payment of the fee stated in the Order, the Licensor grants the Licensee a **non-exclusive, non-transferable, non-sublicensable** license to install and use the Software according to the license type in the Order.

3.2 The Licensee may modify the source code for its own internal use under the purchased license. Modifications remain subject to this Agreement and may be used only where the original Software may be used.

3.3 The Licensee may make backup copies of the Software for archival purposes.

3.4 The license is **perpetual** for the version delivered with the Order, unless it ends under Section 11. The Evaluation license ends automatically after 30 days.

3.5 A Developer Licensee may install the Software for a Client only after the Licensor approves that Client in writing. Each approved Client receives the rights of a Single-Site License for one Site, unless the approval states otherwise. The Developer Licensee must make each Client accept terms at least as protective of the Licensor as this Agreement.

## 4. Restrictions

Unless the Licensor agrees in writing, the Licensee must not:

a) sell, resell, rent, lease, lend, sublicense, or distribute the Software, its source code, or its model weights to any third party;

b) offer the Software, or a service built mainly on it, to third parties as hosted software, software as a service, or a managed monitoring service;

c) publish the Software or any part of it in a public repository, marketplace, or website;

d) use the Software at more Sites than the license allows;

e) remove or change copyright notices, license notices, or attributions;

f) use the trained model weights to train, distill, or benchmark a competing product for distribution;

g) present the Software, or a modified version, as the Licensee's own product;

h) use the Software to identify, track, or profile people in violation of applicable law, or for unlawful discrimination, harassment, or surveillance.

## 5. Ownership

5.1 The Licensor owns all rights, title, and interest in the Software, including all copyrights. This Agreement grants a license. It does not sell or transfer ownership.

5.2 Feedback and suggestions from the Licensee may be used by the Licensor without obligation.

5.3 Custom work ordered separately is governed by the agreement for that work. If that agreement says nothing about ownership, the Licensor keeps ownership of the custom work and the Licensee receives a license to it under the same license type as the Software.

## 6. Third-Party Components

6.1 The Software uses Third-Party Components. Each remains under its own license, as listed in `THIRD_PARTY_NOTICES.md`. Nothing in this Agreement restricts any right the Licensee has under those licenses, and those licenses prevail for those components.

6.2 **Ultralytics.** The detection and tracking functions use the Ultralytics library. Ultralytics publishes it under the GNU Affero General Public License v3.0 (AGPL-3.0) and also offers a separate Ultralytics Enterprise License for closed-source commercial use. The Order states which of the following applies:

a) **Covered by an Ultralytics Enterprise License** obtained by the Licensor or the Licensee. In this case, the Ultralytics components are used under that license.

b) **Not covered.** In this case, the Ultralytics components, and any part of the Software that AGPL-3.0 requires to be licensed with them, are provided under AGPL-3.0. The Licensee is responsible for meeting AGPL-3.0, or for obtaining its own Ultralytics Enterprise License before Production Use.

6.3 The Licensee must keep the attribution notices required by the training data licenses (COCO, Open Images, CAVIAR) when it shares any documentation or model card that the Software includes.

## 7. Delivery, updates, and support

7.1 The Licensor delivers the Software, the model weights, and installation instructions after payment.

7.2 Every paid license includes **30 days of email or platform message support** from delivery, covering installation and use. Support does not cover hardware, networks, cameras, third-party software, or changes made by the Licensee.

7.3 Bug fixes for the purchased version are free during the support period. New major versions, extended support, on-site installation, and custom features are offered for a separate fee.

## 8. Intended use and Licensee responsibilities

8.1 The Software produces **alerts for human review**. A `suspicious` label, alert, or snapshot is not proof of intent, guilt, or a crime. The Licensee must not take legal, disciplinary, or punitive action based on the Software's output alone.

8.2 The Licensee is responsible for using the Software lawfully, including:

a) informing people that CCTV monitoring is in operation, where the law requires it;

b) handling recordings, snapshots, and personal data according to applicable privacy law, such as Indonesia's Personal Data Protection Law (Undang-Undang Nomor 27 Tahun 2022) or the EU General Data Protection Regulation;

c) securing the server, the database, the network, and user accounts;

d) choosing suitable retention periods and deleting data that is no longer needed.

8.3 Detection accuracy depends on camera position, image quality, lighting, and the environment. The Licensee should review alerts and tune thresholds on site.

## 9. Fees and refunds

9.1 Fees, payment terms, and currency are stated in the Order.

9.2 If the Software does not install or run on a computer that meets the requirements in `README.md`, and the Licensor cannot fix the problem within 14 days of being told, the Licensee may request a refund within 30 days of delivery. The Licensee must then delete all copies of the Software.

9.3 Where the purchase was made on a freelance platform, that platform's refund and dispute rules also apply. If they conflict with this Section, the platform's rules prevail for that purchase.

## 10. Warranty disclaimer and limitation of liability

10.1 Except as stated in Section 9.2, the Software is provided **"as is" and "as available"**, without warranty of any kind, express or implied, including warranties of merchantability, fitness for a particular purpose, accuracy, and non-infringement. The Licensor does not warrant that the Software will detect every incident, that it will not produce false alarms, or that it will run without interruption.

10.2 The Software is not a replacement for security personnel, alarm systems, or emergency services.

10.3 To the maximum extent permitted by law, the Licensor is not liable for any indirect, incidental, special, consequential, or punitive damages, or for loss of property, theft, loss of data, loss of profit, or business interruption, arising from the use of or inability to use the Software, even if the Licensor was advised of the possibility.

10.4 To the maximum extent permitted by law, the Licensor's total liability under this Agreement is limited to the fee the Licensee paid for the license in the 12 months before the claim.

## 11. Termination

11.1 This Agreement ends automatically if the Licensee breaches Section 4 or fails to pay the fee, and does not cure the breach within 14 days after written notice.

11.2 When this Agreement ends, the Licensee must stop using the Software and delete all copies, including the model weights and modified versions.

11.3 Sections 4, 5, 6, 8, 10, 11, and 12 survive termination.

## 12. General

12.1 **Governing law.** This Agreement is governed by the laws of the Republic of Indonesia. The parties will first try to settle any dispute by discussion. If that fails within 30 days, the dispute goes to the competent district court in Indonesia, unless the parties agree on another forum in writing.

12.2 **Transfer.** The Licensee may transfer the license to a buyer of its whole business at the licensed Sites, with written notice to the Licensor and written acceptance of this Agreement by the new owner. Any other transfer requires the Licensor's written consent.

12.3 **Entire agreement.** This Agreement and the Order form the entire agreement about the Software. If they conflict, the Order prevails.

12.4 **Severability.** If a court finds any provision unenforceable, the rest of the Agreement stays in force, and the provision is enforced to the maximum extent permitted.

12.5 **Language.** This Agreement is written in English. If a translation is provided, the English version prevails, except where Indonesian law requires an Indonesian version for an Indonesian party (Undang-Undang Nomor 24 Tahun 2009). In that case both versions are equally valid.

12.6 **Contact.** To buy a license, ask for written approval, or send a notice under this Agreement, contact the Licensor through the freelance platform used for the Order or through [github.com/Khairul122](https://github.com/Khairul122).
