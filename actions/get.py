from lib.actions import BaseAction


class GetAction(BaseAction):
    def run(self, table, resource, query):
        s = self.client
        if table == "sc_task":
            r = s.resource(api_path='/table/sc_task')
        response = r.get(query=query)
        #r = s.resource(table=table, query=query)  # pylint: disable=no-member
        #response = r.get_all()  # pylint: disable=no-member
        #print(response)
        # States:
        # 0 - New
        # 1 - In Progress
        # 2 - Waiting
        # 3 - Closed Complete
        # 4 - Closed Incomplete
        output = []
        for record in response.all():
            print('Short description: {}\nState: {}' .format(record['short_description'],record['state']))
            output.append(record)
        #for each_item in response:
        #    output.append(each_item)
        return output
