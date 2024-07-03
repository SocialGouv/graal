import hashlib

from amendements_intelligents.types import ExpertiseID, ExpertMetadata


def create_expertise_dict(
    expertise_descriptions: list[str], experts: list[str]
) -> dict[ExpertiseID, ExpertMetadata]:
    """
    Create a dictionary of expertise descriptions and experts from two lists.
    Merge expertise descriptions that are the same by concatenating experts with a '&'.

    return: A dict where ExpertiseID is the hash of the expertise description and ExpertMetadata is a dict with the expertise description and the associaated concatenated experts.
    """
    created_expertise_dict: dict[
        ExpertiseID, ExpertMetadata
    ] = {}  # {hashed_description: {expertise_description: str, experts: str}
    for desc, expert in zip(expertise_descriptions, experts):
        id = hashlib.sha256(desc.encode()).hexdigest()
        if id in created_expertise_dict:
            # I am not happy about storing multiple experts as a string with a '&' as a
            # separator but ChromaDB does not support storing lists
            created_expertise_dict[id]["experts_as_str"] = (
                f'{created_expertise_dict[id]["experts_as_str"]} & {expert}'
            )
        else:
            created_expertise_dict[id] = {
                "expertise_desc": desc,
                "experts_as_str": expert,
            }
    return created_expertise_dict
