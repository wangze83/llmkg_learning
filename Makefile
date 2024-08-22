.PHONY: dev release push publish

PROJECT_NAME := llmkg_learning
DEV_NAME = $(PROJECT_NAME)-$(USER)

run:
	cd docker && docker-compose -p "$(DEV_NAME)" down && docker-compose -p "$(DEV_NAME)" up --force-recreate

basic_flask_image:
	docker build -f docker/Dockerfile-Flask -t flask_image .