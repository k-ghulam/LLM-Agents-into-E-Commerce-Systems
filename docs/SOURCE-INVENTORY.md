# Source inventory

Only the integrated application is maintained here. This inventory records comparison with the uploaded stages; it is not an assertion that historical source copies are secure.

| Archive stage | Python source files | Browser JavaScript files |
| --- | ---: | ---: |
| Legacy store | 19 | 31 |
| AI proof of concept | 13 | 1 |
| Original integration | 28 | 33 |

The original integration shares 50 Python/JavaScript paths with the legacy store; 11 differ after newline normalization. The POC's `app/chatbot` modules correspond to the integration's `backend/chatbot` modules, while the integrated version adds account/store routes, evaluations, observability and the storefront chat widget.

Excluded from publication: environment files, Logfire local credentials, bytecode/cache folders, experiment notebooks and historical command scripts. The original archive remains the source of historical presentations and notes. `demo_data` is the inherited example importer dataset, not production customer data.
