# esa-survey-graph
## usage

## configuration

Before running the application, you need to set up two configuration files:

### Environment Variables (.env)

Create a `.env` file in the root directory of the project with the following variables:

```env
# access token
ESA_ACCESS_TOKEN=HOGEHOGE # your access token
ESA_TEAM_NAME=HOGE.esa.io # your team name
ESA_RANKING=esa_ranking.png
ESA_RANKING_ALL=esa_ranking_all.png
ESA_RANKING_GROUP=esa_ranking_group.png
YAML_PATH=users.yaml
```

### User Configuration (users.yaml)

Create a `users.yaml` file in the `config` directory to define valid users and groups:

```yaml
valid_users:
  - name1
  - name2
  - name3
  - name4
  - name5
  - name6
  - name7
groups:
  group1:
    - name1
    - name2
    - name3
  group2:
    - name4
  group3:
    - name5
    - name6
```

If you modify the `YAML_PATH` value in `.env`, you have to use that yaml file name.