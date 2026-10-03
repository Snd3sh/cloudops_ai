
from backend.aws_monitor import get_ec2_instances

result = get_ec2_instances()

print("AWS connection successful:", result["success"])
print("Region:", result["region"])
print("Total EC2 instances:", result["total_instances"])

if not result["success"]:
    print("Error:", result["error"])
else:
    for instance in result["instances"]:
        print(instance)