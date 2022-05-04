#!/bin/bash

curl http://172.17.0.3:8080/gen_povs --header "Content-Type: application/json" --request POST --data '{"pid": "YAN01_00010"}'
