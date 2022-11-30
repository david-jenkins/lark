
# get the conenctClient helper
from lark.tools.rpycserver import connectClient

if __name__ == "__main__":
    
    # connect to the service by name
    client = connectClient("This Service")
    
    # call a function on the service
    client.set("hello", 6)
    
    # call another function
    print(client.get("hello"))
    
    # try calling a undefined function
    try:
        client.dosomething("hello")
    except Exception as e:
        print(e)
    
    # optionally close the connection
    client.conn.close()