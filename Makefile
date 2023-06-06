PORT=80

container:
	docker build --build-arg port=$(PORT) --tag $(TAG) --file ./Dockerfile ./

docker-run:
	docker run -p $(EXTPORT):$(PORT) $(TAG)