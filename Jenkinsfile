pipeline {
  agent any

  environment {
        GIT_NAME = "pas.plugins.eea"
        SONARQUBE_TAGS = "www.eea.europa.eu,demo-www.eea.europa.eu,www.eea.europa.eu-en,insitu.copernicus.eu,clmsdemo.devel6cph.eea.europa.eu,forest.eea.europa.eu,land.copernicus.eu,demo-ied.eea.europa.eu,www.ied.eea.europa.eu-en,climate-advisory-board.europa.eu"
    }

  stages {

    stage('Cosmetics') {
      steps {
        parallel(

//  This should be updated to pycodestyle as pep8 doesn't know about type hinting.
//           "PEP8": {
//             node(label: 'docker') {
//               script {
//                 sh '''docker run -i --rm --name="$BUILD_TAG-pep8" -e GIT_SRC="https://github.com/eea/$GIT_NAME.git" -e GIT_NAME="$GIT_NAME" -e GIT_BRANCH="$BRANCH_NAME" -e GIT_CHANGE_ID="$CHANGE_ID" eeacms/pep8'''
//               }
//             }
//           },

          "PyLint": {
            node(label: 'docker') {
              script {
                sh '''docker run -i --rm --name="$BUILD_TAG-pylint" -e GIT_SRC="https://github.com/eea/$GIT_NAME.git" -e GIT_NAME="$GIT_NAME" -e GIT_BRANCH="$BRANCH_NAME" -e GIT_CHANGE_ID="$CHANGE_ID" eeacms/pylint:py3'''
              }
            }
          }

        )
      }
    }

    stage('Code') {
      steps {
        parallel(

          "ZPT Lint": {
            node(label: 'docker') {
              sh '''docker run -i --rm --name="$BUILD_TAG-zptlint" -e GIT_BRANCH="$BRANCH_NAME" -e ADDONS="$GIT_NAME" -e DEVELOP="src/$GIT_NAME" -e GIT_CHANGE_ID="$CHANGE_ID" eeacms/plone-test:4 zptlint'''
            }
          },

          "PyFlakes": {
            node(label: 'docker') {
              sh '''docker run -i --rm --name="$BUILD_TAG-pyflakes" -e GIT_SRC="https://github.com/eea/$GIT_NAME.git" -e GIT_NAME="$GIT_NAME" -e GIT_BRANCH="$BRANCH_NAME" -e GIT_CHANGE_ID="$CHANGE_ID" eeacms/pyflakes:py3'''
            }
          },

          "i18n": {
            node(label: 'docker') {
              sh '''docker run -i --rm --name=$BUILD_TAG-i18n -e GIT_SRC="https://github.com/eea/$GIT_NAME.git" -e GIT_NAME="$GIT_NAME" -e GIT_BRANCH="$BRANCH_NAME" -e GIT_CHANGE_ID="$CHANGE_ID" eeacms/i18ndude'''
            }
          }
        )
      }
    }

    stage('Tests') {
      steps {
        parallel(

          "Coverage": {
            node(label: 'docker') {
              script {
                try {
                  sh '''docker pull eeacms/plone-test:5-python3'''
                  sh '''docker run -i --name="$BUILD_TAG-python3" -e GIT_NAME="$GIT_NAME" -e GIT_BRANCH="$BRANCH_NAME" -e ADDONS="$GIT_NAME[test]" -e DEVELOP="src/$GIT_NAME" -e GIT_CHANGE_ID="$CHANGE_ID" -e PLONE_VERSIONS="requests=>=2.30.0,<3.0" eeacms/plone-test:5-python3 coverage'''
//                   sh '''mkdir -p xunit-reports; docker cp $BUILD_TAG-python3:/plone/instance/parts/xmltestreport/testreports/. xunit-reports/'''
//                   stash name: "xunit-reports", includes: "xunit-reports/*.xml"
                  sh '''docker cp $BUILD_TAG-python3:/plone/instance/src/$GIT_NAME/coverage.xml coverage.xml'''
                  stash name: "coverage.xml", includes: "coverage.xml"
                } finally {
                  sh '''docker rm -v $BUILD_TAG-python3'''
                }
//                 junit 'xunit-reports/*.xml'
              }
            }
          },

/*
          "KGS": {
            node(label: 'docker') {
              sh '''docker run -i --rm --name="$BUILD_TAG-kgs" -e GIT_NAME="$GIT_NAME" -e GIT_BRANCH="$BRANCH_NAME" -e GIT_CHANGE_ID="$CHANGE_ID" eeacms/kgs-devel /debug.sh bin/test --test-path /plone/instance/src/$GIT_NAME -v -vv -s $GIT_NAME'''
            }
          },
*/ /*
          "Plone4": {
            node(label: 'docker') {
              sh '''docker run -i --rm --name="$BUILD_TAG-plone4" -e GIT_BRANCH="$BRANCH_NAME" -e ADDONS="$GIT_NAME" -e DEVELOP="src/$GIT_NAME" -e GIT_CHANGE_ID="$CHANGE_ID" eeacms/plone-test:4 -v -vv -s $GIT_NAME'''
            }
          },

          "Plone5 & Python2": {
            node(label: 'docker') {
              sh '''docker run -i --rm --name="$BUILD_TAG-plone5" -e GIT_BRANCH="$BRANCH_NAME" -e ADDONS="$GIT_NAME" -e DEVELOP="src/$GIT_NAME" -e GIT_CHANGE_ID="$CHANGE_ID" eeacms/plone-test:5 -v -vv -s $GIT_NAME'''
            }
          },
*/
          "Plone5 & Python3": {
            node(label: 'docker') {
              sh '''docker pull eeacms/plone-test:5-python3'''
              sh '''docker run -i --rm --name="$BUILD_TAG-python3" -e GIT_BRANCH="$BRANCH_NAME" -e ADDONS="$GIT_NAME[test]" -e DEVELOP="src/$GIT_NAME" -e GIT_CHANGE_ID="$CHANGE_ID" -e PLONE_VERSIONS="requests=>=2.30.0,<3.0" eeacms/plone-test:5-python3 -v -vv -s $GIT_NAME'''
            }
          },

//          "PloneSaaS": {
//            node(label: 'docker') {
//              sh '''docker pull eeacms/plonesaas-devel; docker run -i --rm --name="$BUILD_TAG-plonesaas" -e GIT_NAME="$GIT_NAME" -e GIT_BRANCH="$BRANCH_NAME" -e GIT_CHANGE_ID="$CHANGE_ID" eeacms/plonesaas-devel /debug.sh bin/test --test-path /plone/instance/src/$GIT_NAME -v -vv -s $GIT_NAME'''
//            }
//          }
        )
      }
    }

    stage('Report to SonarQube') {
      when {
        allOf {
          environment name: 'CHANGE_ID', value: ''
        }
      }
      steps {
        node(label: 'swarm') {
          script{
            checkout scm
//             dir("xunit-reports") {
//               unstash "xunit-reports"
//             }
//             unstash "xunit-reports"
            unstash "coverage.xml"
            def scannerHome = tool 'SonarQubeScanner';
            def nodeJS = tool 'NodeJS11';
            withSonarQubeEnv('Sonarqube') {
                sh '''sed -i "s|/plone/instance/src/$GIT_NAME|$(pwd)|g" coverage.xml'''
                sh "export PATH=$PATH:${scannerHome}/bin:${nodeJS}/bin; sonar-scanner -Dsonar.python.xunit.skipDetails=true -Dsonar.python.version=3.8,3.12 -Dsonar.python.coverage.reportPaths=coverage.xml -Dsonar.sources=\$(pwd) -Dsonar.projectKey=$GIT_NAME-$BRANCH_NAME -Dsonar.projectVersion=$BRANCH_NAME-$BUILD_NUMBER"
                sh '''try=2; while [ \$try -gt 0 ]; do curl -s -XPOST -u "${SONAR_AUTH_TOKEN}:" "${SONAR_HOST_URL}api/project_tags/set?project=${GIT_NAME}-${BRANCH_NAME}&tags=${SONARQUBE_TAGS},${BRANCH_NAME}" > set_tags_result; if [ \$(grep -ic error set_tags_result ) -eq 0 ]; then try=0; else cat set_tags_result; echo "... Will retry"; sleep 60; try=\$(( \$try - 1 )); fi; done'''
            }
          }
        }
      }
    }

    stage('Pull Request') {
      when {
        not {
          environment name: 'CHANGE_ID', value: ''
        }
        environment name: 'CHANGE_TARGET', value: 'master'
      }
      steps {
        node(label: 'docker') {
          script {
            if ( env.CHANGE_BRANCH != "develop" &&  !( env.CHANGE_BRANCH.startsWith("hotfix")) ) {
                error "Pipeline aborted due to PR not made from develop or hotfix branch"
            }
           withCredentials([string(credentialsId: 'eea-jenkins-token', variable: 'GITHUB_TOKEN')]) {
            sh '''docker run -i --rm --name="$BUILD_TAG-gitflow-pr" -e GIT_CHANGE_BRANCH="$CHANGE_BRANCH" -e GIT_CHANGE_AUTHOR="$CHANGE_AUTHOR" -e GIT_CHANGE_TITLE="$CHANGE_TITLE" -e GIT_TOKEN="$GITHUB_TOKEN" -e GIT_BRANCH="$BRANCH_NAME" -e GIT_CHANGE_ID="$CHANGE_ID" -e GIT_ORG="$GIT_ORG" -e GIT_NAME="$GIT_NAME" eeacms/gitflow'''
           }
          }
        }
      }
    }

    stage('Release') {
      when {
        allOf {
          environment name: 'CHANGE_ID', value: ''
          branch 'master'
        }
      }
      steps {
        node(label: 'docker') {
          withCredentials([[$class: 'UsernamePasswordMultiBinding', credentialsId: 'eea-jenkins', usernameVariable: 'EGGREPO_USERNAME', passwordVariable: 'EGGREPO_PASSWORD'],string(credentialsId: 'eea-jenkins-token', variable: 'GITHUB_TOKEN'),[$class: 'UsernamePasswordMultiBinding', credentialsId: 'pypi-jenkins', usernameVariable: 'PYPI_USERNAME', passwordVariable: 'PYPI_PASSWORD']]) {
            sh '''docker run -i --rm --name="$BUILD_TAG-gitflow-master" -e GIT_BRANCH="$BRANCH_NAME" -e EGGREPO_USERNAME="$EGGREPO_USERNAME" -e EGGREPO_PASSWORD="$EGGREPO_PASSWORD" -e GIT_NAME="$GIT_NAME"  -e PYPI_USERNAME="$PYPI_USERNAME"  -e PYPI_PASSWORD="$PYPI_PASSWORD" -e GIT_ORG="$GIT_ORG" -e GIT_TOKEN="$GITHUB_TOKEN" eeacms/gitflow'''
          }
        }
      }
    }

  }

  post {
    changed {
      script {
        def url = "${env.BUILD_URL}/display/redirect"
        def status = currentBuild.currentResult
        def subject = "${status}: Job '${env.JOB_NAME} [${env.BUILD_NUMBER}]'"
        def summary = "${subject} (${url})"
        def details = """<h1>${env.JOB_NAME} - Build #${env.BUILD_NUMBER} - ${status}</h1>
                         <p>Check console output at <a href="${url}">${env.JOB_BASE_NAME} - #${env.BUILD_NUMBER}</a></p>
                      """

        def color = '#FFFF00'
        if (status == 'SUCCESS') {
          color = '#00FF00'
        } else if (status == 'FAILURE') {
          color = '#FF0000'
        }

        emailext (subject: '$DEFAULT_SUBJECT', to: '$DEFAULT_RECIPIENTS', body: details)
      }
    }
  }
}
