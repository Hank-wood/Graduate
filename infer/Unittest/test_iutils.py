from iutils import longestIncreasingSubsequence


nums = [0, 8, 4, 12, 2, 10, 6, 14, 1, 9, 5, 13, 3, 11, 7, 15]
lis, index_list = longestIncreasingSubsequence(nums)
assert lis == [0, 2, 6, 9, 11, 15]
assert index_list == [0, 4, 6, 9, 13, 15]
for time, index in zip(*longestIncreasingSubsequence(nums)):
    print(time, index)

nums = [2, 5, 3, 7, 11, 8, 10, 13, 6]
lis, index_list = longestIncreasingSubsequence(nums)
assert lis == [2, 3, 7, 8, 10, 13]
assert index_list == [0, 2, 3, 5, 6, 7]
