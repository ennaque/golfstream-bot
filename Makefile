.DEFAULT_GOAL := all

dockerc := docker-compose -f .docker/docker-compose.yml
pgsql_env := pgsql-variables.env
nginx_conf := nginx.conf
env := .env

build_env:
	@echo "Start building env"
	@test ! -f 'docker/${pgsql_env}' && (echo 'Copy file ...'; cp -v docker/${pgsql_env}.dist docker/${pgsql_env}) || echo 'File '${pgsql_env} 'exists.'
	@test ! -f 'docker/nginx/${nginx_conf}' && (echo 'Copy file ...'; cp -v docker/nginx/${nginx_conf}.dist docker/nginx/${nginx_conf}) || echo 'File '${nginx_conf} 'exists.'
	@test ! -f 'docker/${env}' && (echo 'Copy file ...'; cp -v docker/${env}.dist docker/${env}) || echo 'Docker file '${env} 'exists.'