app:
  image:
    repository: ${CI_REGISTRY}/${CI_PROJECT_NAMESPACE}/${CI_PROJECT_NAME}/frontend
    tag: ${DEPLOYMENT_ENV}-${CI_COMMIT_SHA}
api:
  image:
    repository: ${CI_REGISTRY}/${CI_PROJECT_NAMESPACE}/${CI_PROJECT_NAME}/api
    tag: ${DEPLOYMENT_ENV}-${CI_COMMIT_SHA}
