# LICENSES.md

Status: Example baseline only
Last updated: 2026-05-12

## RVL-CDIP Dataset

This project uses the RVL-CDIP document image dataset for academic/research purposes as part of the SE Factory AIE Bootcamp Week 6 project.

Dataset source: http://www.cs.cmu.edu/~aharley/rvl-cdip/

The dataset contains 16 document layout classes:

- letter
- form
- email
- handwritten
- advertisement
- scientific report
- scientific publication
- specification
- file folder
- news article
- budget
- invoice
- presentation
- questionnaire
- resume
- memo

The full dataset is not committed to this repository. Training and full test-set evaluation are performed in Colab. The repository only includes the required project artifacts:

- trained classifier weights
- model card
- 50-image golden set
- expected golden-set outputs

## Usage Note

The RVL-CDIP dataset is used here only for academic/research and bootcamp evaluation purposes. This repository does not redistribute the full RVL-CDIP dataset.

## Model Artifacts

The model weights in `backend/app/classifier/models/classifier.pt` are derived from training/fine-tuning on RVL-CDIP. The model card should document:

- dataset used
- backbone
- pretrained weights enum
- freeze policy
- test metrics
- SHA-256 hash
- environment fingerprint

## Third-Party Services and Libraries

This project also uses open-source libraries and local Docker services, including but not limited to:

- FastAPI
- SQLAlchemy
- Alembic
- fastapi-users
- Casbin
- fastapi-cache2
- Redis / RQ
- MinIO
- HashiCorp Vault dev mode
- atmoz/sftp
- PyTorch
- torchvision

Final license details for dependencies should be reviewed before any non-academic distribution.
